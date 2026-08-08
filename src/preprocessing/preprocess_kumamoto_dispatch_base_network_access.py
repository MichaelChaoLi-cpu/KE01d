#!/usr/bin/env python3
"""Copy confirmed candidate dispatch-base network-access records."""
from pathlib import Path
from geoparquet_utils import copy_selected_geoparquet

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "../KE01b/data/processed/kumamoto_dispatch_base_network_access_preprocessed.parquet").resolve()
DESTINATION = ROOT / "data/processed/kumamoto_dispatch_base_network_access_preprocessed.parquet"
COLUMNS = ["Fire Facility Name", "Municipality Code", "Fire Facility Type Code", "Address", "Geometry", "Fire Facility Type", "Candidate Dispatch Base", "Dispatch Base Node ID", "Network Snap Distance (m)", "Network Snap Accepted", "Access Road Edge ID", "Access Edge Fraction"]

rows, columns = copy_selected_geoparquet(SOURCE, DESTINATION, COLUMNS)
print(f"Saved {rows:,} rows x {columns} cols -> {DESTINATION.relative_to(ROOT)}")
