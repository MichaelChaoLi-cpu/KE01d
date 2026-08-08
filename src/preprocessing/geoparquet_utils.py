#!/usr/bin/env python3
"""Shared, provenance-preserving GeoParquet preprocessing helpers."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


TARGET_CRS = "EPSG:6668"
PROJ_DATA = Path("/opt/homebrew/share/proj")
OGR2OGR = Path("/opt/homebrew/bin/ogr2ogr")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _geo_metadata(table: pa.Table) -> bytes:
    metadata = table.schema.metadata or {}
    geo = metadata.get(b"geo")
    if geo is None:
        raise ValueError("Source does not contain GeoParquet metadata")
    return geo


def _validate_geo_metadata(geo: bytes, expected_crs: str = TARGET_CRS) -> None:
    metadata = json.loads(geo)
    primary = metadata.get("primary_column")
    if primary != "Geometry":
        raise ValueError(f"Expected primary geometry 'Geometry', found {primary!r}")
    crs_text = json.dumps(metadata.get("columns", {}).get(primary, {}).get("crs"))
    expected_code = expected_crs.split(":")[-1]
    if expected_code not in crs_text:
        raise ValueError(f"Expected {expected_crs} in GeoParquet CRS metadata")


def _write_table(table: pa.Table, destination: Path, geo: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    metadata = dict(table.schema.metadata or {})
    metadata.pop(b"pandas", None)
    metadata[b"geo"] = geo
    table = table.replace_schema_metadata(metadata)
    pq.write_table(table, destination, compression="zstd")


def copy_selected_geoparquet(
    source: Path,
    destination: Path,
    columns: Iterable[str],
) -> tuple[int, int]:
    """Select columns from an existing EPSG:6668 GeoParquet without decoding WKB."""
    columns = list(columns)
    table = pq.read_table(source, columns=columns)
    geo = _geo_metadata(table)
    _validate_geo_metadata(geo)
    _write_table(table, destination, geo)
    return table.num_rows, table.num_columns


def _run_ogr(command: list[str]) -> None:
    if not OGR2OGR.exists():
        raise FileNotFoundError(f"ogr2ogr not found at {OGR2OGR}")
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError(
            "ogr2ogr failed\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )


def reproject_selected_geoparquet(
    source: Path,
    destination: Path,
    columns: Iterable[str],
    source_crs: str,
    boolean_columns: Iterable[str] = (),
) -> tuple[int, int]:
    """Reproject selected fields with GDAL and retain nullable booleans."""
    columns = list(columns)
    with tempfile.TemporaryDirectory(prefix="ke01d_reproject_") as temp_dir:
        temp_output = Path(temp_dir) / "output.parquet"
        command = [
            str(OGR2OGR),
            "--config",
            "PROJ_DATA",
            str(PROJ_DATA),
            "-f",
            "Parquet",
            str(temp_output),
            str(source),
            "-s_srs",
            source_crs,
            "-t_srs",
            TARGET_CRS,
            "-select",
            ",".join(columns),
        ]
        _run_ogr(command)
        temporary = pq.read_table(temp_output)
        geo = _geo_metadata(temporary)
        _validate_geo_metadata(geo)
        frame = temporary.to_pandas()
        frame = frame.drop(columns=["Geometry_bbox"], errors="ignore")
        frame = frame[columns]
        for column in boolean_columns:
            frame[column] = frame[column].astype("boolean")
        table = pa.Table.from_pandas(frame, preserve_index=False)
        _write_table(table, destination, geo)
    return len(frame), len(frame.columns)


def preprocess_p21_layer(
    archive: Path,
    member: str,
    destination: Path,
    field_map: dict[str, str],
    integer_columns: Iterable[str],
    float_columns: Iterable[str],
    zero_to_missing: Iterable[str],
) -> tuple[int, int]:
    """Decode, reproject, and standardize an MLIT P21 shapefile member."""
    integer_columns = list(integer_columns)
    float_columns = list(float_columns)
    zero_to_missing = list(zero_to_missing)
    source = f"/vsizip/{archive.resolve()}/{member}"
    layer = Path(member).stem
    select_parts = [f'"{raw}" AS "{readable}"' for raw, readable in field_map.items()]
    select_parts.append('geometry AS "Geometry"')
    sql = f'SELECT {", ".join(select_parts)} FROM "{layer}"'

    with tempfile.TemporaryDirectory(prefix="ke01d_p21_") as temp_dir:
        temp_output = Path(temp_dir) / "output.parquet"
        command = [
            str(OGR2OGR),
            "--config",
            "PROJ_DATA",
            str(PROJ_DATA),
            "--config",
            "SHAPE_ENCODING",
            "CP932",
            "-f",
            "Parquet",
            str(temp_output),
            source,
            "-s_srs",
            "EPSG:4612",
            "-t_srs",
            TARGET_CRS,
            "-dialect",
            "SQLite",
            "-sql",
            sql,
        ]
        _run_ogr(command)
        temporary = pq.read_table(temp_output)
        geo = _geo_metadata(temporary)
        _validate_geo_metadata(geo)
        frame = temporary.to_pandas().drop(columns=["Geometry_bbox"], errors="ignore")

        for column in field_map.values():
            if column not in integer_columns and column not in float_columns:
                frame[column] = frame[column].astype("string").str.strip()
        for column in integer_columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Int64")
        for column in float_columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Float64")
        for column in zero_to_missing:
            frame[column] = frame[column].mask(frame[column] == 0)

        frame["Source Reference Year"] = pd.Series(2010, index=frame.index, dtype="Int64")
        frame["Dataset Edition Year"] = pd.Series(2012, index=frame.index, dtype="Int64")
        frame["Historical Capacity Only"] = pd.Series(True, index=frame.index, dtype="boolean")
        ordered = [
            *field_map.values(),
            "Geometry",
            "Source Reference Year",
            "Dataset Edition Year",
            "Historical Capacity Only",
        ]
        frame = frame[ordered]
        table = pa.Table.from_pandas(frame, preserve_index=False)
        _write_table(table, destination, geo)
    return len(frame), len(frame.columns)
