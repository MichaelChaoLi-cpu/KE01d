#!/usr/bin/env python3
"""Resolve current shelters, attach road nodes, and construct separate demand scenarios."""
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from geoparquet_utils import _geo_metadata, _write_table
from round2_utils import attach_nearest_network_node, resolve_facility_locations

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/shelters_current_preprocessed.parquet"
STAGING = ROOT / "data/processed/kumamoto_staging_site_candidates_preprocessed.parquet"
NODES = ROOT / "data/processed/kumamoto_routable_road_nodes_preprocessed.parquet"
EDGES = ROOT / "data/processed/kumamoto_routable_road_edges_preprocessed.parquet"
DESTINATION = ROOT / "data/processed/shelter_water_demand_network_access_preprocessed.parquet"

base = pd.read_parquet(SOURCE)
base = resolve_facility_locations(base, "Shelter Name", STAGING)
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
