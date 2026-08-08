#!/usr/bin/env python3
"""Copy confirmed routable road-node fields into the current project."""
from pathlib import Path
from geoparquet_utils import copy_selected_geoparquet

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "../KE01b/data/processed/kumamoto_routable_road_nodes_preprocessed.parquet").resolve()
DESTINATION = ROOT / "data/processed/kumamoto_routable_road_nodes_preprocessed.parquet"
COLUMNS = ["Network Node ID", "Network Component ID", "Network Analysis Eligible", "Vertical Level", "Geometry"]

rows, columns = copy_selected_geoparquet(SOURCE, DESTINATION, COLUMNS)
print(f"Saved {rows:,} rows x {columns} cols -> {DESTINATION.relative_to(ROOT)}")
