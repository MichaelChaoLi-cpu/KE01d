#!/usr/bin/env python3
"""Resolve announced water points conservatively and attach accepted road nodes."""
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from geoparquet_utils import _geo_metadata, _write_table
from round2_utils import (
    attach_nearest_network_node,
    point_wkb,
    resolve_facility_locations,
    transform_xy,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/emergency_water_points_preprocessed.parquet"
STAGING = ROOT / "data/processed/kumamoto_staging_site_candidates_preprocessed.parquet"
NODES = ROOT / "data/processed/kumamoto_routable_road_nodes_preprocessed.parquet"
EDGES = ROOT / "data/processed/kumamoto_routable_road_edges_preprocessed.parquet"
DESTINATION = ROOT / "data/processed/emergency_water_points_network_access_preprocessed.parquet"

# Coordinates recovered from the public support-map data linked by the 2026-08-08
# Yatsushiro City water-point announcement. Facility identities were cross-checked
# against official municipal facility/address pages. These explicit overrides are
# limited to the 19 announcement names that were unresolved by the conservative
# exact-one-geometry staging-candidate rule.
ANNOUNCEMENT_LINKED_MAP_COORDINATES = {
    ("氷川町", "宮原振興局"): (130.6825688, 32.5558812, "google-places"),
    ("八代市", "第二中学校"): (130.6241940, 32.5104270, "nominatim"),
    ("八代市", "代陽コミセン"): (130.5973210, 32.50709197, "mlit-p05"),
    ("八代市", "八千把コミセン"): (130.6142001, 32.51843403, "mlit-p05"),
    ("八代市", "太田郷コミセン"): (130.6300745, 32.51527398, "mlit-p05"),
    ("八代市", "昭和コミセン"): (130.6036567, 32.55974813, "mlit-p05"),
    ("八代市", "鏡コミセン"): (130.6447742, 32.5619385, "nominatim"),
    ("八代市", "千丁コミセン"): (130.6336380, 32.5350333, "mlit-p05"),
    ("八代市", "松高コミセン"): (130.5922685, 32.51935482, "mlit-p05"),
    ("八代市", "麦島コミセン"): (130.5927080, 32.4975230, "manual"),
    ("八代市", "龍峯コミセン"): (130.6646270, 32.5288430, "gsi"),
    ("八代市", "日奈久コミセン"): (130.5788348, 32.43501291, "mlit-p05"),
    ("八代市", "八代支援学校"): (130.5792216, 32.5214746, "nominatim"),
    ("八代市", "金剛コミセン"): (130.5882210, 32.4699060, "google-places"),
    ("八代市", "宮地コミセン"): (130.6398610, 32.4994030, "manual"),
    ("八代市", "二見コミセン"): (130.5588880, 32.4072120, "manual"),
    ("八代市", "文政小学校"): (130.6332480, 32.5607010, "manual"),
    ("八代市", "市役所本庁舎西側"): (130.6018575, 32.5074629, "manual"),
    ("八代市", "鏡町野崎公民館"): (130.6323631, 32.5920400, "google-places"),
}

frame = pd.read_parquet(SOURCE)
frame = resolve_facility_locations(frame, "Water Point Name", STAGING)

override_indices = []
override_lonlat = []
override_providers = []
for index, row in frame.loc[frame["Location Resolution Status"].eq("unmatched")].iterrows():
    key = (row["Municipality"], row["Water Point Name"])
    override = ANNOUNCEMENT_LINKED_MAP_COORDINATES.get(key)
    if override is not None:
        longitude, latitude, provider = override
        override_indices.append(index)
        override_lonlat.append((longitude, latitude))
        override_providers.append(provider)

if override_indices:
    override_projected = transform_xy(override_lonlat, "EPSG:4326", "EPSG:6668")
    for index, (longitude, latitude), (x, y), provider in zip(
        override_indices, override_lonlat, override_projected, override_providers
    ):
        frame.at[index, "Longitude"] = longitude
        frame.at[index, "Latitude"] = latitude
        frame.at[index, "Geometry"] = point_wkb(x, y)
        frame.at[index, "Location Resolution Status"] = "matched_announcement_linked_map_coordinate"
        frame.at[index, "Location Resolution Source"] = (
            f"yatsushiro_announcement_linked_support_map:{provider}"
        )

remaining_unmatched = frame["Location Resolution Status"].eq("unmatched")
if remaining_unmatched.any():
    missing = frame.loc[remaining_unmatched, ["Municipality", "Water Point Name"]]
    raise ValueError(f"Water-point locations remain unresolved:\n{missing.to_string(index=False)}")

frame = attach_nearest_network_node(frame, "Water Point Node ID", NODES, EDGES, 250.0)
columns = ["Municipality", "Water Point Name", "Valid From Date", "Valid To Date", "Opening Time", "Closing Time", "Allocation Basis", "Allocation Limit (L)", "Water Type", "Source Status Time", "Latitude", "Longitude", "Geometry", "Location Resolution Status", "Location Resolution Source", "Location Match Candidate Record Count", "Location Match Candidate Geometry Count", "Water Point Node ID", "Network Snap Distance (m)", "Network Snap Accepted", "Access Road Edge ID", "Access Edge Fraction"]
frame = frame[columns]
geo = _geo_metadata(pq.read_table(NODES))
_write_table(pa.Table.from_pandas(frame, preserve_index=False), DESTINATION, geo)
print(f"Saved {len(frame):,} rows x {len(frame.columns)} cols -> {DESTINATION.relative_to(ROOT)}")
print(f"Location status: {frame['Location Resolution Status'].value_counts(dropna=False).to_dict()}")
print(f"Network accepted: {frame['Network Snap Accepted'].value_counts(dropna=False).to_dict()}")
