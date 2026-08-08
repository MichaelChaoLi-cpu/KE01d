#!/usr/bin/env python3
"""Dissolve five Kumamoto City wards into one of 45 reporting municipalities."""
from pathlib import Path
import tempfile
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from geoparquet_utils import OGR2OGR, PROJ_DATA, _geo_metadata, _validate_geo_metadata, _write_table
from round2_utils import run

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/kumamoto_administrative_areas_preprocessed.parquet"
DESTINATION = ROOT / "data/processed/kumamoto_reporting_municipalities_preprocessed.parquet"

sql = '''
SELECT CASE WHEN "Municipality Name" = '熊本市' THEN '43100' ELSE "Municipality Code" END
         AS "Reporting Municipality Code",
       "Municipality Name" AS "Reporting Municipality Name",
       COUNT(*) AS "Constituent Administrative Unit Count",
       CASE WHEN "Municipality Name" = '熊本市' THEN 1 ELSE 0 END
         AS "Kumamoto City Ward Dissolved",
       ST_Union(Geometry) AS Geometry
FROM "kumamoto_administrative_areas_preprocessed"
GROUP BY "Municipality Name",
         CASE WHEN "Municipality Name" = '熊本市' THEN '43100' ELSE "Municipality Code" END
'''

with tempfile.TemporaryDirectory(prefix="ke01d_reporting_municipalities_") as directory:
    temporary = Path(directory) / "reporting.parquet"
    run([
        str(OGR2OGR), "--config", "PROJ_DATA", str(PROJ_DATA), "-f", "Parquet",
        str(temporary), str(SOURCE), "-dialect", "SQLite", "-sql", sql,
    ])
    table = pq.read_table(temporary)
    geo = _geo_metadata(table)
    _validate_geo_metadata(geo)
    frame = table.to_pandas().drop(columns=["Geometry_bbox"], errors="ignore")
    frame["Constituent Administrative Unit Count"] = pd.to_numeric(
        frame["Constituent Administrative Unit Count"], errors="coerce"
    ).astype("Int64")
    frame["Kumamoto City Ward Dissolved"] = frame["Kumamoto City Ward Dissolved"].astype("boolean")
    frame = frame[["Reporting Municipality Code", "Reporting Municipality Name", "Constituent Administrative Unit Count", "Kumamoto City Ward Dissolved", "Geometry"]]
    _write_table(pa.Table.from_pandas(frame, preserve_index=False), DESTINATION, geo)
print(f"Saved {len(frame):,} rows x {len(frame.columns)} cols -> {DESTINATION.relative_to(ROOT)}")
