#!/usr/bin/env python3
"""Keep older-population measures at their disclosure-group support."""
from pathlib import Path
from geoparquet_utils import copy_selected_geoparquet

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "../KE01b/data/processed/kumamoto_population_disclosure_groups_preprocessed.parquet").resolve()
DESTINATION = ROOT / "data/processed/kumamoto_population_disclosure_groups_preprocessed.parquet"
COLUMNS = ["Disclosure Group Code", "Geometry", "Disclosure Group Size", "Suppressed Source Mesh Count", "Total Population", "Total Households", "General Households", "Population Age 65+", "Population Age 75+", "Population Age 85+", "One-Person Households", "Households with Member Age 65+", "Older Single-Person Households", "Older Couple Households", "Population Age 65+ Share", "Population Age 75+ Share", "Population Age 85+ Share", "Older Single-Person Household Share", "Older Couple Household Share"]

rows, columns = copy_selected_geoparquet(SOURCE, DESTINATION, COLUMNS)
print(f"Saved {rows:,} rows x {columns} cols -> {DESTINATION.relative_to(ROOT)}")
