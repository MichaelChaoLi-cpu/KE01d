#!/usr/bin/env python3
"""Resolve current shelters, attach road nodes, and construct separate demand scenarios."""
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from geoparquet_utils import _geo_metadata, _write_table
from round2_utils import (
    attach_nearest_network_node,
    normalize_facility_name,
    parse_point_wkb,
    resolve_facility_locations,
    transform_xy,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/shelters_current_preprocessed.parquet"
STAGING = ROOT / "data/processed/kumamoto_staging_site_candidates_preprocessed.parquet"
NODES = ROOT / "data/processed/kumamoto_routable_road_nodes_preprocessed.parquet"
EDGES = ROOT / "data/processed/kumamoto_routable_road_edges_preprocessed.parquet"
DESTINATION = ROOT / "data/processed/shelter_water_demand_network_access_preprocessed.parquet"


def normalize_yatsushiro_shelter_name(value: object) -> str:
    """Normalize exact names while allowing the official 'Yatsushiro City' prefix."""
    return normalize_facility_name(value).removeprefix("八代市立")


def fill_from_current_official_shelter_layers(
    frame: pd.DataFrame, staging_path: Path
) -> pd.DataFrame:
    """Resolve remaining shelters using a documented current-source hierarchy."""
    staging = pd.read_parquet(
        staging_path,
        columns=[
            "Candidate Staging Site ID",
            "Candidate Staging Site Type",
            "Candidate Staging Site Name",
            "Geometry",
        ],
    )
    hierarchy = [
        (
            "Designated shelter",
            "SHELTER::E43202",
            "matched_current_designated_shelter_exact",
            "gsi_designated_shelter_exact_yatsushiro",
        ),
        (
            "Emergency evacuation site",
            "EVACUATION::E43202",
            "matched_current_emergency_evacuation_site_exact",
            "gsi_emergency_evacuation_site_exact_yatsushiro",
        ),
    ]
    result = frame.copy()
    result_names = result["Shelter Name"].map(normalize_yatsushiro_shelter_name)

    for candidate_type, id_prefix, status, source in hierarchy:
        candidates = staging.loc[
            staging["Candidate Staging Site Type"].eq(candidate_type)
            & staging["Candidate Staging Site ID"].astype("string").str.startswith(id_prefix),
            ["Candidate Staging Site Name", "Geometry"],
        ].copy()
        candidates["_normalized"] = candidates["Candidate Staging Site Name"].map(
            normalize_yatsushiro_shelter_name
        )
        grouped = candidates.groupby("_normalized", dropna=False)["Geometry"]
        unique_geometry = {
            normalized: bytes(geometries[0])
            for normalized, group in grouped
            if len(geometries := group.dropna().unique()) == 1
        }
        unresolved = result["Location Resolution Status"].eq("unmatched")
        for index in result.index[unresolved]:
            geometry = unique_geometry.get(result_names.loc[index])
            if geometry is None:
                continue
            result.at[index, "Geometry"] = geometry
            result.at[index, "Location Resolution Status"] = status
            result.at[index, "Location Resolution Source"] = source

    new_match = result["Latitude"].isna() & result["Geometry"].notna()
    projected = [parse_point_wkb(value) for value in result.loc[new_match, "Geometry"]]
    geographic = transform_xy(projected, "EPSG:6668", "EPSG:4326")
    for index, (longitude, latitude) in zip(result.index[new_match], geographic):
        result.at[index, "Longitude"] = longitude
        result.at[index, "Latitude"] = latitude
    if result["Location Resolution Status"].eq("unmatched").any():
        names = result.loc[
            result["Location Resolution Status"].eq("unmatched"), "Shelter Name"
        ].tolist()
        raise ValueError(f"Official shelter hierarchy left unresolved names: {names}")
    return result


base = pd.read_parquet(SOURCE)
base = resolve_facility_locations(base, "Shelter Name", STAGING)
base = fill_from_current_official_shelter_layers(base, STAGING)
base = attach_nearest_network_node(base, "Shelter Node ID", NODES, EDGES, 250.0)
parts = []
for label, per_capita in [("minimum", 3.0), ("basic", 10.0), ("extended", 20.0)]:
    part = base.copy()
    part["Demand Scenario"] = label
    part["Per Capita Water Demand (L/person/day)"] = per_capita
    part["Estimated Shelter Water Demand (L/day)"] = part["Evacuee People"] * per_capita
    part["Shelter Demand Accounting Status"] = "separate_not_added_to_resident_demand"
    parts.append(part)
frame = pd.concat(parts, ignore_index=True)
columns = ["Municipality", "Shelter Number", "Shelter Name", "District", "Maximum Capacity", "Evacuee Households", "Evacuee People", "Water Status", "Electricity Status", "Air Conditioning Status", "Toilet Count", "Portable Toilet Count", "Snapshot Time", "Latitude", "Longitude", "Geometry", "Location Resolution Status", "Location Resolution Source", "Location Match Candidate Record Count", "Location Match Candidate Geometry Count", "Shelter Node ID", "Network Snap Distance (m)", "Network Snap Accepted", "Access Road Edge ID", "Access Edge Fraction", "Demand Scenario", "Per Capita Water Demand (L/person/day)", "Estimated Shelter Water Demand (L/day)", "Shelter Demand Accounting Status"]
frame = frame[columns]
geo = _geo_metadata(pq.read_table(NODES))
_write_table(pa.Table.from_pandas(frame, preserve_index=False), DESTINATION, geo)
print(f"Saved {len(frame):,} rows x {len(frame.columns)} cols -> {DESTINATION.relative_to(ROOT)}")
print(f"Unique shelter location status: {base['Location Resolution Status'].value_counts(dropna=False).to_dict()}")
print(f"Unique shelter network accepted: {base['Network Snap Accepted'].value_counts(dropna=False).to_dict()}")
