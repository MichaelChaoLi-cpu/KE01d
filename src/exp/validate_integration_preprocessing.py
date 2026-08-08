#!/usr/bin/env python3
"""Validate integrated preprocessing outputs and record immutable source checksums."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/preprocessing"))
from geoparquet_utils import sha256_file  # noqa: E402


EXPECTED = {
    "kumamoto_administrative_areas_preprocessed.parquet": (49, 7),
    "kumamoto_population_mesh_125m_preprocessed.parquet": (62_945, 10),
    "kumamoto_population_disclosure_groups_preprocessed.parquet": (36_657, 19),
    "kumamoto_population_mesh_network_access_preprocessed.parquet": (62_945, 8),
    "kumamoto_population_group_network_access_preprocessed.parquet": (36_657, 9),
    "kumamoto_routable_road_edges_preprocessed.parquet": (390_234, 21),
    "kumamoto_staging_site_candidates_preprocessed.parquet": (6_105, 14),
    "kumamoto_fire_stations_2012_preprocessed.parquet": (94, 7),
    "kumamoto_water_supply_areas_2010_preprocessed.parquet": (385, 10),
    "kumamoto_water_treatment_facilities_2010_preprocessed.parquet": (153, 9),
}

SOURCES = {
    "kumamoto_administrative_areas_preprocessed.parquet": "../KE01b/data/processed/kumamoto_administrative_areas_preprocessed.parquet",
    "kumamoto_population_mesh_125m_preprocessed.parquet": "../KE01b/data/processed/kumamoto_population_mesh_125m_preprocessed.parquet",
    "kumamoto_population_disclosure_groups_preprocessed.parquet": "../KE01b/data/processed/kumamoto_population_disclosure_groups_preprocessed.parquet",
    "kumamoto_population_mesh_network_access_preprocessed.parquet": "../KE01b/data/processed/kumamoto_population_mesh_network_access_preprocessed.parquet",
    "kumamoto_population_group_network_access_preprocessed.parquet": "../KE01b/data/processed/kumamoto_population_group_network_access_preprocessed.parquet",
    "kumamoto_routable_road_edges_preprocessed.parquet": "../KE01b/data/processed/kumamoto_routable_road_edges_preprocessed.parquet",
    "kumamoto_staging_site_candidates_preprocessed.parquet": "../KE01c/data/results/derived/staging_site_candidates.parquet",
    "kumamoto_fire_stations_2012_preprocessed.parquet": "../KE01b/data/processed/kumamoto_fire_stations_2012_preprocessed.parquet",
    "kumamoto_water_supply_areas_2010_preprocessed.parquet": "data/raw/reference/mlit_p21_2012/P21-12_43_GML.zip",
    "kumamoto_water_treatment_facilities_2010_preprocessed.parquet": "data/raw/reference/mlit_p21_2012/P21-12_43_GML.zip",
}


def geo_summary(path: Path) -> dict[str, object]:
    metadata = pq.read_schema(path).metadata or {}
    geo = json.loads(metadata[b"geo"])
    primary = geo["primary_column"]
    crs = geo["columns"][primary]["crs"]
    return {
        "primary_geometry": primary,
        "crs_has_epsg_6668": "6668" in json.dumps(crs),
    }


def main() -> None:
    checks: list[dict[str, object]] = []
    failures: list[str] = []
    manifest: list[dict[str, object]] = []

    for name, expected_shape in EXPECTED.items():
        output = ROOT / "data/processed" / name
        metadata = pq.read_metadata(output)
        actual_shape = (metadata.num_rows, metadata.num_columns)
        geo = geo_summary(output)
        passed = actual_shape == expected_shape and geo["primary_geometry"] == "Geometry" and geo["crs_has_epsg_6668"]
        checks.append({
            "check": f"shape_crs:{name}",
            "passed": passed,
            "observed": {"rows": actual_shape[0], "columns": actual_shape[1], **geo},
        })
        if not passed:
            failures.append(f"Unexpected shape or CRS for {name}: {actual_shape}, {geo}")

        source_text = SOURCES[name]
        source = (ROOT / source_text).resolve()
        manifest.append({
            "source_path": source_text,
            "source_sha256": sha256_file(source),
            "source_bytes": source.stat().st_size,
            "output_path": str(output.relative_to(ROOT)),
            "output_rows": actual_shape[0],
            "output_columns": actual_shape[1],
        })

    mesh_access = pd.read_parquet(
        ROOT / "data/processed/kumamoto_population_mesh_network_access_preprocessed.parquet",
        columns=["Network Snap Accepted"],
    )
    group_access = pd.read_parquet(
        ROOT / "data/processed/kumamoto_population_group_network_access_preprocessed.parquet",
        columns=["Network Snap Accepted"],
    )
    staging = pd.read_parquet(
        ROOT / "data/processed/kumamoto_staging_site_candidates_preprocessed.parquet",
        columns=["Network Snap Accepted", "Staging Demand Node ID"],
    )
    areas = pd.read_parquet(
        ROOT / "data/processed/kumamoto_water_supply_areas_2010_preprocessed.parquet"
    )
    facilities = pd.read_parquet(
        ROOT / "data/processed/kumamoto_water_treatment_facilities_2010_preprocessed.parquet"
    )

    semantic_checks = {
        "mesh_rejected_snaps_retained": int((mesh_access["Network Snap Accepted"] == False).sum()) == 48,  # noqa: E712
        "group_rejected_snaps_retained": int((group_access["Network Snap Accepted"] == False).sum()) == 7,  # noqa: E712
        "staging_unmatched_retained": int(staging["Staging Demand Node ID"].isna().sum()) == 159,
        "p21_area_zero_population_to_missing": int(areas["Served Population"].isna().sum()) == 312 and not bool((areas["Served Population"] == 0).any()),
        "p21_area_zero_capacity_to_missing": int(areas["Maximum Daily Supply (m3/day)"].isna().sum()) == 312 and not bool((areas["Maximum Daily Supply (m3/day)"] == 0).any()),
        "p21_facility_zero_capacity_to_missing": int(facilities["Maximum Daily Supply (m3/day)"].isna().sum()) == 17 and not bool((facilities["Maximum Daily Supply (m3/day)"] == 0).any()),
        "p21_area_historical_flag": bool(areas["Historical Capacity Only"].all()) and set(areas["Source Reference Year"].dropna()) == {2010},
        "p21_facility_historical_flag": bool(facilities["Historical Capacity Only"].all()) and set(facilities["Source Reference Year"].dropna()) == {2010},
    }
    for name, passed in semantic_checks.items():
        checks.append({"check": name, "passed": passed})
        if not passed:
            failures.append(name)

    exp_dir = ROOT / "data/exp/data-preprocessing"
    exp_dir.mkdir(parents=True, exist_ok=True)
    with (exp_dir / "integration_source_manifest.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(manifest[0]))
        writer.writeheader()
        writer.writerows(manifest)
    report = {
        "status": "passed" if not failures else "failed",
        "checks": checks,
        "failures": failures,
    }
    (exp_dir / "integration_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Validation status: {report['status']}")
    print(f"Checks passed: {sum(bool(item['passed']) for item in checks)}/{len(checks)}")
    print(f"Source manifest rows: {len(manifest)}")
    if failures:
        raise SystemExit("; ".join(failures))


if __name__ == "__main__":
    main()
