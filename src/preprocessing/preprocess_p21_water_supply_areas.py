#!/usr/bin/env python3
"""Preprocess historical MLIT P21 water-supply-area polygons."""
from pathlib import Path
from geoparquet_utils import preprocess_p21_layer

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "data/raw/reference/mlit_p21_2012/P21-12_43_GML.zip"
DESTINATION = ROOT / "data/processed/kumamoto_water_supply_areas_2010_preprocessed.parquet"
FIELD_MAP = {
    "P21A_001": "Water Utility Operator",
    "P21A_002": "Water Service Name",
    "P21A_003": "Water Service Type Code",
    "P21A_004": "Served Population",
    "P21A_005": "Maximum Daily Supply (m3/day)",
    "検査ID": "P21 Inspection ID",
}

rows, columns = preprocess_p21_layer(
    ARCHIVE,
    "P21-12a_43.shp",
    DESTINATION,
    FIELD_MAP,
    integer_columns=["Water Service Type Code", "Served Population", "P21 Inspection ID"],
    float_columns=["Maximum Daily Supply (m3/day)"],
    zero_to_missing=["Served Population", "Maximum Daily Supply (m3/day)"],
)
print(f"Saved {rows:,} rows x {columns} cols -> {DESTINATION.relative_to(ROOT)}")
