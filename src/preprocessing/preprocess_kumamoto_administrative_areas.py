#!/usr/bin/env python3
"""Select the 49 source administrative units without dissolving city wards."""
from pathlib import Path
from geoparquet_utils import copy_selected_geoparquet

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "../KE01b/data/processed/kumamoto_administrative_areas_preprocessed.parquet").resolve()
DESTINATION = ROOT / "data/processed/kumamoto_administrative_areas_preprocessed.parquet"
COLUMNS = ["Municipality Code", "Prefecture Name", "District Name", "Municipality Name", "Ward Name", "Municipality Label", "Geometry"]

rows, columns = copy_selected_geoparquet(SOURCE, DESTINATION, COLUMNS)
print(f"Saved {rows:,} rows x {columns} cols -> {DESTINATION.relative_to(ROOT)}")
