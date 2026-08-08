#!/usr/bin/env python3
"""Keep every mesh access record, including rejected network snaps."""
from pathlib import Path
from geoparquet_utils import copy_selected_geoparquet

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "../KE01b/data/processed/kumamoto_population_mesh_network_access_preprocessed.parquet").resolve()
DESTINATION = ROOT / "data/processed/kumamoto_population_mesh_network_access_preprocessed.parquet"
COLUMNS = ["Mesh Code", "Geometry", "Analysis Unit ID", "Demand Node ID", "Network Snap Distance (m)", "Network Snap Accepted", "Access Road Edge ID", "Access Edge Fraction"]

rows, columns = copy_selected_geoparquet(SOURCE, DESTINATION, COLUMNS)
print(f"Saved {rows:,} rows x {columns} cols -> {DESTINATION.relative_to(ROOT)}")
