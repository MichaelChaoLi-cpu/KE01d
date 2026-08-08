#!/usr/bin/env python3
"""Select routable road-edge inputs; travel time and availability remain scenarios."""
from pathlib import Path
from geoparquet_utils import copy_selected_geoparquet

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "../KE01b/data/processed/kumamoto_routable_road_edges_preprocessed.parquet").resolve()
DESTINATION = ROOT / "data/processed/kumamoto_routable_road_edges_preprocessed.parquet"
COLUMNS = ["Road Edge ID", "Road Section ID", "From Node ID", "To Node ID", "Network Component ID", "Road Length (m)", "Assumed Speed (km/h)", "Baseline Edge Travel Time (min)", "Hazard Exposure Class", "Emergency Route Membership", "Road Available", "Network Analysis Eligible", "Route ID", "Route Name", "Road Category", "Road State", "Vertical Level", "Width Category", "Toll Category", "Secondary Mesh Code", "Geometry"]

rows, columns = copy_selected_geoparquet(SOURCE, DESTINATION, COLUMNS)
print(f"Saved {rows:,} rows x {columns} cols -> {DESTINATION.relative_to(ROOT)}")
