#!/usr/bin/env python3
"""Shared helpers for second-round spatial linkage and scenario preprocessing."""
from __future__ import annotations

import json
import math
import re
import struct
import subprocess
import tempfile
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from geoparquet_utils import OGR2OGR, PROJ_DATA, _geo_metadata, _validate_geo_metadata, _write_table


GDALTRANSFORM = Path("/opt/homebrew/bin/gdaltransform")


def run(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )


def write_geo_frame(frame: pd.DataFrame, destination: Path, geo: bytes) -> None:
    table = pa.Table.from_pandas(frame, preserve_index=False)
    _write_table(table, destination, geo)


def normalize_facility_name(value: object) -> str:
    if pd.isna(value):
        return ""
    normalized = unicodedata.normalize("NFKC", str(value))
    normalized = re.sub(r"[\s　・･()（）]", "", normalized)
    normalized = normalized.replace("コミセン", "コミュニティセンター")
    normalized = normalized.replace("小学校体育館", "小学校")
    normalized = normalized.replace("中学校体育館", "中学校")
    return normalized


def normalize_route_name(value: object) -> str | None:
    if pd.isna(value) or not str(value).strip():
        return None
    normalized = unicodedata.normalize("NFKC", str(value))
    return re.sub(r"[\s　・･()（）]", "", normalized)


def point_wkb(x: float, y: float) -> bytes:
    return struct.pack("<BIdd", 1, 1, float(x), float(y))


def parse_point_wkb(value: object) -> tuple[float, float]:
    data = bytes(value)
    endian = "<" if data[0] == 1 else ">"
    geometry_type = struct.unpack_from(endian + "I", data, 1)[0]
    base_type = geometry_type & 0xFF
    if base_type != 1:
        raise ValueError(f"Expected WKB Point, found geometry type {geometry_type}")
    return struct.unpack_from(endian + "dd", data, 5)


def transform_xy(
    coordinates: list[tuple[float, float]], source_crs: str, target_crs: str
) -> list[tuple[float, float]]:
    if not coordinates:
        return []
    payload = "".join(f"{x} {y}\n" for x, y in coordinates)
    command = [
        str(GDALTRANSFORM),
        "--config",
        "PROJ_DATA",
        str(PROJ_DATA),
        "-s_srs",
        source_crs,
        "-t_srs",
        target_crs,
    ]
    completed = subprocess.run(command, input=payload, capture_output=True, text=True, check=False)
    if completed.returncode:
        raise RuntimeError(completed.stderr)
    result = []
    for line in completed.stdout.splitlines():
        values = line.split()
        result.append((float(values[0]), float(values[1])))
    if len(result) != len(coordinates):
        raise ValueError("gdaltransform returned an unexpected coordinate count")
    return result


def weighted_quantile(values: pd.Series, weights: pd.Series, quantile: float) -> float:
    valid = values.notna() & weights.notna() & (weights > 0)
    array = values[valid].to_numpy(dtype=float)
    weight = weights[valid].to_numpy(dtype=float)
    if not len(array):
        return math.nan
    order = np.argsort(array)
    array = array[order]
    weight = weight[order]
    cutoff = quantile * weight.sum()
    return float(array[np.searchsorted(np.cumsum(weight), cutoff, side="left")])


def build_mesh_municipality_links(
    mesh_path: Path, municipality_path: Path
) -> pd.DataFrame:
    """Assign mesh polygons by point-on-surface, then maximum overlap for residuals."""
    with tempfile.TemporaryDirectory(prefix="ke01d_mesh_link_") as temporary_directory:
        temp = Path(temporary_directory)
        mesh_points = temp / "mesh_points.parquet"
        gpkg = temp / "join.gpkg"
        point_links = temp / "point_links.parquet"
        layer = mesh_path.stem
        sql_points = (
            'SELECT "Mesh Code", "Total Population", "Total Households", '
            f'ST_PointOnSurface(Geometry) AS Geometry FROM "{layer}"'
        )
        run([
            str(OGR2OGR), "--config", "PROJ_DATA", str(PROJ_DATA), "-f", "Parquet",
            str(mesh_points), str(mesh_path), "-dialect", "SQLite", "-sql", sql_points,
        ])
        run([
            str(OGR2OGR), "--config", "PROJ_DATA", str(PROJ_DATA), "-f", "GPKG",
            str(gpkg), str(municipality_path), "-nln", "municipalities", "-nlt", "PROMOTE_TO_MULTI",
        ])
        run([
            str(OGR2OGR), "--config", "PROJ_DATA", str(PROJ_DATA), "-f", "GPKG",
            "-update", str(gpkg), str(mesh_points), "-nln", "mesh_points",
        ])
        sql_link = '''
            SELECT p."Mesh Code", a."Reporting Municipality Code",
                   a."Reporting Municipality Name"
            FROM mesh_points p
            JOIN rtree_municipalities_Geometry r
              ON ST_X(p.Geometry) BETWEEN r.minx AND r.maxx
             AND ST_Y(p.Geometry) BETWEEN r.miny AND r.maxy
            JOIN municipalities a ON a.fid = r.id
            WHERE ST_Intersects(p.Geometry, a.Geometry)
        '''
        run([
            str(OGR2OGR), "--config", "PROJ_DATA", str(PROJ_DATA), "-f", "Parquet",
            str(point_links), str(gpkg), "-dialect", "SQLite", "-sql", sql_link, "-nlt", "NONE",
        ])
        links = pd.read_parquet(point_links)
        links = links.drop(columns=["Geometry_bbox"], errors="ignore")
        duplicate = links["Mesh Code"].duplicated(keep=False)
        unique = links.loc[~duplicate].copy()
        unique["Spatial Join Status"] = "point_unique"

        mesh = pd.read_parquet(mesh_path)
        unresolved_codes = set(mesh["Mesh Code"]) - set(unique["Mesh Code"])
        unresolved = mesh[mesh["Mesh Code"].isin(unresolved_codes)][
            ["Mesh Code", "Total Population", "Total Households", "Geometry"]
        ]
        fallback_rows: list[dict[str, object]] = []
        if len(unresolved):
            unresolved_path = temp / "unresolved.parquet"
            source_geo = _geo_metadata(pq.read_table(mesh_path))
            write_geo_frame(unresolved, unresolved_path, source_geo)
            run([
                str(OGR2OGR), "--config", "PROJ_DATA", str(PROJ_DATA), "-f", "GPKG",
                "-update", str(gpkg), str(unresolved_path), "-nln", "unresolved_meshes",
            ])
            overlaps = temp / "overlaps.parquet"
            sql_overlap = '''
                SELECT u."Mesh Code", a."Reporting Municipality Code",
                       a."Reporting Municipality Name",
                       ST_Area(ST_Intersection(u.Geometry, a.Geometry)) AS overlap_area
                FROM unresolved_meshes u
                JOIN rtree_unresolved_meshes_Geometry ur ON ur.id = u.fid
                JOIN rtree_municipalities_Geometry r
                  ON r.minx <= ur.maxx AND r.maxx >= ur.minx
                 AND r.miny <= ur.maxy AND r.maxy >= ur.miny
                JOIN municipalities a ON a.fid = r.id
                WHERE ST_Intersects(u.Geometry, a.Geometry)
            '''
            run([
                str(OGR2OGR), "--config", "PROJ_DATA", str(PROJ_DATA), "-f", "Parquet",
                str(overlaps), str(gpkg), "-dialect", "SQLite", "-sql", sql_overlap, "-nlt", "NONE",
            ])
            overlap_frame = pd.read_parquet(overlaps).drop(columns=["Geometry_bbox"], errors="ignore")
            if len(overlap_frame):
                overlap_frame = overlap_frame.sort_values(
                    ["Mesh Code", "overlap_area", "Reporting Municipality Code"],
                    ascending=[True, False, True],
                ).drop_duplicates("Mesh Code")
                for record in overlap_frame.to_dict("records"):
                    fallback_rows.append({
                        "Mesh Code": record["Mesh Code"],
                        "Reporting Municipality Code": record["Reporting Municipality Code"],
                        "Reporting Municipality Name": record["Reporting Municipality Name"],
                        "Spatial Join Status": "maximum_overlap",
                    })

        result = pd.concat(
            [
                unique[["Mesh Code", "Reporting Municipality Code", "Reporting Municipality Name", "Spatial Join Status"]],
                pd.DataFrame(fallback_rows),
            ],
            ignore_index=True,
        )
        result = mesh.merge(result, on="Mesh Code", how="left")
        result["Spatial Join Status"] = result["Spatial Join Status"].fillna("unmatched")
        return result


def resolve_facility_locations(
    frame: pd.DataFrame,
    name_column: str,
    staging_path: Path,
) -> pd.DataFrame:
    """Retain accepted coordinates, then accept only exact names with one unique geometry."""
    staging = pd.read_parquet(
        staging_path, columns=["Candidate Staging Site Name", "Geometry"]
    )
    staging["_normalized"] = staging["Candidate Staging Site Name"].map(normalize_facility_name)
    grouped = staging.groupby("_normalized", dropna=False)
    record_counts = grouped.size().to_dict()
    geometry_counts = grouped["Geometry"].nunique(dropna=True).to_dict()
    unique_geometry = {}
    for normalized, group in grouped:
        geometries = group["Geometry"].dropna().unique()
        if len(geometries) == 1:
            unique_geometry[normalized] = bytes(geometries[0])

    result = frame.copy()
    result["Location Resolution Status"] = result["Location Resolution Status"].astype("string")
    normalized_names = result[name_column].map(normalize_facility_name)
    result["Location Match Candidate Record Count"] = normalized_names.map(record_counts).fillna(0).astype("Int64")
    result["Location Match Candidate Geometry Count"] = normalized_names.map(geometry_counts).fillna(0).astype("Int64")
    result["Location Resolution Source"] = pd.Series("unresolved", index=result.index, dtype="string")
    result["Geometry"] = pd.Series([None] * len(result), dtype="object")

    existing = result["Latitude"].notna() & result["Longitude"].notna()
    existing_coordinates = list(zip(result.loc[existing, "Longitude"], result.loc[existing, "Latitude"]))
    transformed = transform_xy(existing_coordinates, "EPSG:4326", "EPSG:6668")
    for index, (x, y) in zip(result.index[existing], transformed):
        result.at[index, "Geometry"] = point_wkb(x, y)
    result.loc[existing, "Location Resolution Source"] = "2012_facility_exact"

    for index in result.index[~existing]:
        normalized = normalized_names.loc[index]
        geometry = unique_geometry.get(normalized)
        if geometry is not None:
            result.at[index, "Geometry"] = geometry
            result.at[index, "Location Resolution Source"] = "staging_candidate_exact_unique_geometry"
            result.at[index, "Location Resolution Status"] = "matched_exact_candidate_unique_geometry"

    new_match = (~existing) & result["Geometry"].notna()
    projected = [parse_point_wkb(value) for value in result.loc[new_match, "Geometry"]]
    geographic = transform_xy(projected, "EPSG:6668", "EPSG:4326")
    for index, (longitude, latitude) in zip(result.index[new_match], geographic):
        result.at[index, "Longitude"] = longitude
        result.at[index, "Latitude"] = latitude
    return result


def attach_nearest_network_node(
    frame: pd.DataFrame,
    node_id_column: str,
    road_nodes_path: Path,
    road_edges_path: Path,
    threshold_m: float = 250.0,
) -> pd.DataFrame:
    nodes = pd.read_parquet(road_nodes_path, columns=["Network Node ID", "Geometry"])
    node_lonlat = [parse_point_wkb(value) for value in nodes["Geometry"]]
    node_xy = np.asarray(transform_xy(node_lonlat, "EPSG:6668", "EPSG:6670"), dtype=float)
    edges = pd.read_parquet(
        road_edges_path, columns=["Road Edge ID", "From Node ID", "To Node ID"]
    )
    access: dict[str, tuple[str, float]] = {}
    for edge_id, from_node, to_node in edges.itertuples(index=False, name=None):
        access.setdefault(str(from_node), (str(edge_id), 0.0))
        access.setdefault(str(to_node), (str(edge_id), 1.0))

    result = frame.copy()
    result[node_id_column] = pd.Series(pd.NA, index=result.index, dtype="string")
    result["Network Snap Distance (m)"] = pd.Series(pd.NA, index=result.index, dtype="Float64")
    result["Network Snap Accepted"] = pd.Series(pd.NA, index=result.index, dtype="boolean")
    result["Access Road Edge ID"] = pd.Series(pd.NA, index=result.index, dtype="string")
    result["Access Edge Fraction"] = pd.Series(pd.NA, index=result.index, dtype="Float64")

    located = result["Geometry"].notna()
    locations_lonlat = [parse_point_wkb(value) for value in result.loc[located, "Geometry"]]
    locations_xy = transform_xy(locations_lonlat, "EPSG:6668", "EPSG:6670")
    for index, (x, y) in zip(result.index[located], locations_xy):
        squared = (node_xy[:, 0] - x) ** 2 + (node_xy[:, 1] - y) ** 2
        nearest = int(np.argmin(squared))
        distance = float(math.sqrt(float(squared[nearest])))
        accepted = distance <= threshold_m
        result.at[index, "Network Snap Distance (m)"] = distance
        result.at[index, "Network Snap Accepted"] = accepted
        if accepted:
            node_id = str(nodes.iloc[nearest]["Network Node ID"])
            result.at[index, node_id_column] = node_id
            edge = access.get(node_id)
            if edge:
                result.at[index, "Access Road Edge ID"] = edge[0]
                result.at[index, "Access Edge Fraction"] = edge[1]
    return result
