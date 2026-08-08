#!/usr/bin/env python3
"""Resolve announced water points conservatively and attach accepted road nodes."""
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from geoparquet_utils import _geo_metadata, _write_table
from round2_utils import attach_nearest_network_node, resolve_facility_locations

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/emergency_water_points_preprocessed.parquet"
STAGING = ROOT / "data/processed/kumamoto_staging_site_candidates_preprocessed.parquet"
NODES = ROOT / "data/processed/kumamoto_routable_road_nodes_preprocessed.parquet"
EDGES = ROOT / "data/processed/kumamoto_routable_road_edges_preprocessed.parquet"
DESTINATION = ROOT / "data/processed/emergency_water_points_network_access_preprocessed.parquet"

frame = pd.read_parquet(SOURCE)
frame = resolve_facility_locations(frame, "Water Point Name", STAGING)
frame = attach_nearest_network_node(frame, "Water Point Node ID", NODES, EDGES, 250.0)
columns = ["Municipality", "Water Point Name", "Valid From Date", "Valid To Date", "Opening Time", "Closing Time", "Allocation Basis", "Allocation Limit (L)", "Water Type", "Source Status Time", "Latitude", "Longitude", "Geometry", "Location Resolution Status", "Location Resolution Source", "Location Match Candidate Record Count", "Location Match Candidate Geometry Count", "Water Point Node ID", "Network Snap Distance (m)", "Network Snap Accepted", "Access Road Edge ID", "Access Edge Fraction"]
frame = frame[columns]
geo = _geo_metadata(pq.read_table(NODES))
_write_table(pa.Table.from_pandas(frame, preserve_index=False), DESTINATION, geo)
print(f"Saved {len(frame):,} rows x {len(frame.columns)} cols -> {DESTINATION.relative_to(ROOT)}")
print(f"Location status: {frame['Location Resolution Status'].value_counts(dropna=False).to_dict()}")
print(f"Network accepted: {frame['Network Snap Accepted'].value_counts(dropna=False).to_dict()}")
