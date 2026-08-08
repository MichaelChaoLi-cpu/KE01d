#!/usr/bin/env python3
"""Reproject candidate staging sites and retain unmatched candidates."""
from pathlib import Path
from geoparquet_utils import reproject_selected_geoparquet

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "../KE01c/data/results/derived/staging_site_candidates.parquet").resolve()
DESTINATION = ROOT / "data/processed/kumamoto_staging_site_candidates_preprocessed.parquet"
COLUMNS = ["Candidate Staging Site ID", "Candidate Staging Site Type", "Candidate Staging Site Name", "Candidate Source Status", "Staging Source Priority", "Geometry", "Access Mesh Code", "Staging Demand Node ID", "Staging Access Network Snap Distance (m)", "Network Snap Accepted", "Staging-to-Mesh Distance (m)", "Total Population", "Candidate Network Eligible", "Screened Staging Candidate"]

rows, columns = reproject_selected_geoparquet(SOURCE, DESTINATION, COLUMNS, "EPSG:6670", ["Network Snap Accepted"])
print(f"Saved {rows:,} rows x {columns} cols -> {DESTINATION.relative_to(ROOT)}")
