#!/usr/bin/env python3
"""Select the 125 m population mesh and disclosure metadata."""
from pathlib import Path
from geoparquet_utils import copy_selected_geoparquet

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "../KE01b/data/processed/kumamoto_population_mesh_125m_preprocessed.parquet").resolve()
DESTINATION = ROOT / "data/processed/kumamoto_population_mesh_125m_preprocessed.parquet"
COLUMNS = ["Mesh Code", "Geometry", "Disclosure Group Code", "Disclosure Group Size", "Disclosure Status", "Aggregation Destination Mesh Code", "Aggregated Source Mesh Codes", "Total Population", "Total Households", "General Households"]

rows, columns = copy_selected_geoparquet(SOURCE, DESTINATION, COLUMNS)
print(f"Saved {rows:,} rows x {columns} cols -> {DESTINATION.relative_to(ROOT)}")
