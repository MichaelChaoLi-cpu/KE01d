#!/usr/bin/env python3
"""Match every timestamped restriction geometry to routable road edges with diagnostics."""
from pathlib import Path
import json
import tempfile
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from geoparquet_utils import OGR2OGR, PROJ_DATA, _geo_metadata, _write_table
from round2_utils import normalize_route_name, run

ROOT = Path(__file__).resolve().parents[2]
RESTRICTIONS = ROOT / "data/processed/road_restrictions_preprocessed.parquet"
ROADS = ROOT / "data/processed/kumamoto_routable_road_edges_preprocessed.parquet"
DESTINATION = ROOT / "data/processed/road_restriction_edge_matches_preprocessed.parquet"

source = pd.read_parquet(RESTRICTIONS)
source["Restriction Observation ID"] = [f"RR-{index:06d}" for index in range(1, len(source) + 1)]
source["_geometry_type"] = source["Geometry JSON"].map(lambda value: json.loads(value)["type"])
source["_resolved_status"] = source["Restriction Status"].astype("string").combine_first(
    source["Restriction Start Status"].astype("string")
)

with tempfile.TemporaryDirectory(prefix="ke01d_restriction_match_") as directory:
    temp = Path(directory)
    geojson = temp / "restrictions.geojson"
    geographic = temp / "restrictions_6668.parquet"
    gpkg = temp / "match.gpkg"
    candidates_path = temp / "candidates.parquet"
    features = []
    for original_index, row in source.iterrows():
        observation_id = row["Restriction Observation ID"]
        features.append({
            "type": "Feature",
            "geometry": json.loads(row["Geometry JSON"]),
            "properties": {
                "Restriction Observation ID": observation_id,
                "Restriction Route Name": None if pd.isna(row["Route Name"]) else str(row["Route Name"]),
                "Geometry Type": row["_geometry_type"],
            },
        })
    geojson.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False), encoding="utf-8")

    run([
        str(OGR2OGR), "--config", "PROJ_DATA", str(PROJ_DATA), "-f", "Parquet",
        str(geographic), str(geojson), "-s_srs", "EPSG:4326", "-t_srs", "EPSG:6668",
        "-lco", "GEOMETRY_NAME=Geometry",
    ])
    run([
        str(OGR2OGR), "--config", "PROJ_DATA", str(PROJ_DATA), "-f", "GPKG",
        str(gpkg), str(geojson), "-s_srs", "EPSG:4326", "-t_srs", "EPSG:6670",
        "-nln", "restrictions", "-lco", "GEOMETRY_NAME=Geometry",
    ])
    run([
        str(OGR2OGR), "--config", "PROJ_DATA", str(PROJ_DATA), "-f", "GPKG", "-update",
        str(gpkg), str(ROADS), "-s_srs", "EPSG:6668", "-t_srs", "EPSG:6670",
        "-nln", "roads", "-select", "Road Edge ID,Route Name", "-lco", "GEOMETRY_NAME=Geometry",
    ])
    sql = '''
        SELECT x."Restriction Observation ID", x."Restriction Route Name",
               x."Geometry Type", e."Road Edge ID", e."Route Name" AS "Road Route Name",
               ST_Distance(x.Geometry, e.Geometry) AS "Match Distance"
        FROM restrictions x
        JOIN rtree_restrictions_Geometry xr ON xr.id = x.fid
        JOIN rtree_roads_Geometry er
          ON er.minx <= xr.maxx + 250 AND er.maxx >= xr.minx - 250
         AND er.miny <= xr.maxy + 250 AND er.maxy >= xr.miny - 250
        JOIN roads e ON e.fid = er.id
        WHERE ST_Distance(x.Geometry, e.Geometry) <= 250
    '''
    run([
        str(OGR2OGR), "--config", "PROJ_DATA", str(PROJ_DATA), "-f", "Parquet",
        str(candidates_path), str(gpkg), "-dialect", "SQLite", "-sql", sql, "-nlt", "NONE",
    ])
    candidates = pd.read_parquet(candidates_path).drop(columns=["Geometry_bbox"], errors="ignore")
    geometry_table = pq.read_table(geographic)
    geo = _geo_metadata(geometry_table)
    geometry_frame = geometry_table.to_pandas().drop(columns=["Geometry_bbox"], errors="ignore")
    geometry_lookup = dict(zip(geometry_frame["Restriction Observation ID"], geometry_frame["Geometry"]))

records = []
for index, row in source.iterrows():
    observation_id = row["Restriction Observation ID"]
    group = candidates[candidates["Restriction Observation ID"].eq(observation_id)].copy()
    primary_threshold = 100.0 if row["_geometry_type"] == "Point" else 50.0
    primary = group[group["Match Distance"].le(primary_threshold)].sort_values(
        ["Match Distance", "Road Edge ID"]
    )
    if len(primary):
        selected = primary
        method = "point_nearest_100m" if row["_geometry_type"] == "Point" else "line_buffer_50m"
        status = "matched_primary"
        candidate_count = len(primary)
    elif len(group):
        selected = group.sort_values(["Match Distance", "Road Edge ID"]).head(1)
        method = "nearest_edge_250m_fallback"
        status = "matched_fallback"
        candidate_count = len(group)
    else:
        selected = pd.DataFrame([{"Road Edge ID": pd.NA, "Road Route Name": pd.NA, "Match Distance": pd.NA}])
        method = "none"
        status = "unmatched"
        candidate_count = 0
    for candidate in selected.to_dict("records"):
        restriction_route = normalize_route_name(row["Route Name"])
        road_route = normalize_route_name(candidate.get("Road Route Name"))
        agreement = pd.NA if restriction_route is None or road_route is None else restriction_route == road_route
        records.append({
            "Restriction Observation ID": observation_id,
            "Snapshot Time": row["Snapshot Time"],
            "Route Name": row["Route Name"],
            "Restriction Status": row["_resolved_status"],
            "Restriction Reason": row["Restriction Reason"],
            "Geometry": geometry_lookup[observation_id],
            "Matched Road Edge ID": candidate.get("Road Edge ID"),
            "Road Edge Match Distance (m)": candidate.get("Match Distance"),
            "Route Name Agreement": agreement,
            "Road Edge Match Candidate Count": candidate_count,
            "Road Edge Match Method": method,
            "Road Edge Match Status": status,
        })

frame = pd.DataFrame(records)
frame["Road Edge Match Distance (m)"] = pd.to_numeric(frame["Road Edge Match Distance (m)"], errors="coerce").astype("Float64")
frame["Route Name Agreement"] = frame["Route Name Agreement"].astype("boolean")
frame["Road Edge Match Candidate Count"] = frame["Road Edge Match Candidate Count"].astype("Int64")
columns = ["Restriction Observation ID", "Snapshot Time", "Route Name", "Restriction Status", "Restriction Reason", "Geometry", "Matched Road Edge ID", "Road Edge Match Distance (m)", "Route Name Agreement", "Road Edge Match Candidate Count", "Road Edge Match Method", "Road Edge Match Status"]
frame = frame[columns]
_write_table(pa.Table.from_pandas(frame, preserve_index=False), DESTINATION, geo)
print(f"Saved {len(frame):,} rows x {len(frame.columns)} cols -> {DESTINATION.relative_to(ROOT)}")
print(f"Match status: {frame['Road Edge Match Status'].value_counts(dropna=False).to_dict()}")
