#!/usr/bin/env python3
"""Select historical fire facilities as candidate dispatch bases only."""
from pathlib import Path
from geoparquet_utils import copy_selected_geoparquet

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "../KE01b/data/processed/kumamoto_fire_stations_2012_preprocessed.parquet").resolve()
DESTINATION = ROOT / "data/processed/kumamoto_fire_stations_2012_preprocessed.parquet"
COLUMNS = ["Fire Facility Name", "Municipality Code", "Fire Facility Type Code", "Address", "Geometry", "Fire Facility Type", "Candidate Dispatch Base"]

rows, columns = copy_selected_geoparquet(SOURCE, DESTINATION, COLUMNS)
print(f"Saved {rows:,} rows x {columns} cols -> {DESTINATION.relative_to(ROOT)}")
