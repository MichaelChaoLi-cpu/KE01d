#!/usr/bin/env python3
"""Validate second-round linkage, demand, access, road-match, and parameter outputs."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/preprocessing"))
from geoparquet_utils import sha256_file  # noqa: E402

EXPECTED = {
    "kumamoto_routable_road_nodes_preprocessed.parquet": (314_391, 5),
    "kumamoto_dispatch_base_network_access_preprocessed.parquet": (81, 12),
    "reporting_unit_municipality_crosswalk_preprocessed.parquet": (19, 8),
    "kumamoto_reporting_municipalities_preprocessed.parquet": (45, 5),
    "population_mesh_outage_demand_scenarios_preprocessed.parquet": (566_505, 18),
    "municipality_outage_demand_scenarios_preprocessed.parquet": (414, 20),
    "emergency_water_points_network_access_preprocessed.parquet": (36, 22),
    "shelter_water_demand_network_access_preprocessed.parquet": (123, 29),
    "road_restriction_edge_matches_preprocessed.parquet": (98_884, 12),
    "emergency_water_scenario_parameters_preprocessed.parquet": (35, 7),
}
GEO_FILES = set(EXPECTED) - {
    "reporting_unit_municipality_crosswalk_preprocessed.parquet",
    "emergency_water_scenario_parameters_preprocessed.parquet",
}
SOURCES = {
    "../KE01b/data/processed/kumamoto_routable_road_nodes_preprocessed.parquet": "data/processed/kumamoto_routable_road_nodes_preprocessed.parquet",
    "../KE01b/data/processed/kumamoto_dispatch_base_network_access_preprocessed.parquet": "data/processed/kumamoto_dispatch_base_network_access_preprocessed.parquet",
}


def check(condition: bool, name: str, details: object, checks: list[dict], failures: list[str]) -> None:
    checks.append({"check": name, "passed": bool(condition), "details": details})
    if not condition:
        failures.append(name)


def main() -> None:
    checks: list[dict] = []
    failures: list[str] = []
    decisions = json.loads((ROOT / "data/exp/data-preprocessing/decisions.json").read_text(encoding="utf-8"))["datasets"]

    for name, shape in EXPECTED.items():
        path = ROOT / "data/processed" / name
        metadata = pq.read_metadata(path)
        actual = (metadata.num_rows, metadata.num_columns)
        check(actual == shape, f"shape:{name}", {"expected": shape, "actual": actual}, checks, failures)
        if name in GEO_FILES:
            geo = json.loads((pq.read_schema(path).metadata or {})[b"geo"])
            crs = geo["columns"][geo["primary_column"]]["crs"]
            valid = geo["primary_column"] == "Geometry" and "6668" in json.dumps(crs)
            check(valid, f"geo:{name}", {"primary": geo["primary_column"], "epsg6668": "6668" in json.dumps(crs)}, checks, failures)

    for _, specification in decisions.items():
        output = ROOT / specification["output"]
        expected_columns = [item["readable_name"] for item in specification["variables"]]
        actual_columns = pq.read_schema(output).names
        check(actual_columns == expected_columns, f"schema:{specification['output']}", {"columns": len(actual_columns)}, checks, failures)
        check(all(name.isascii() for name in actual_columns), f"ascii:{specification['output']}", {}, checks, failures)

    crosswalk = pd.read_parquet(ROOT / "data/processed/reporting_unit_municipality_crosswalk_preprocessed.parquet")
    status_counts = crosswalk["Municipality Match Status"].value_counts().to_dict()
    check(status_counts == {"exact_official_name": 15, "outside_kumamoto_scope": 3, "joint_operator_unallocated": 1}, "crosswalk_statuses", status_counts, checks, failures)

    municipalities = pd.read_parquet(ROOT / "data/processed/kumamoto_reporting_municipalities_preprocessed.parquet")
    city = municipalities[municipalities["Reporting Municipality Code"].eq("43100")]
    check(len(city) == 1 and int(city.iloc[0]["Constituent Administrative Unit Count"]) == 5 and bool(city.iloc[0]["Kumamoto City Ward Dissolved"]), "kumamoto_city_dissolve", {}, checks, failures)

    mesh = pd.read_parquet(ROOT / "data/processed/population_mesh_outage_demand_scenarios_preprocessed.parquet")
    unique_mesh = mesh.drop_duplicates("Mesh Code")
    spatial_counts = unique_mesh["Spatial Join Status"].value_counts().to_dict()
    check(mesh["Mesh Code"].value_counts().eq(9).all(), "nine_scenarios_per_mesh", {}, checks, failures)
    check(spatial_counts == {"point_unique": 62_507, "maximum_overlap": 432, "unmatched": 6}, "mesh_spatial_statuses", spatial_counts, checks, failures)
    check(int(unique_mesh["Total Population"].sum()) == 1_738_301 and int(unique_mesh["Total Households"].sum()) == 719_154, "mesh_totals_preserved", {}, checks, failures)
    identity = (mesh["Estimated Water Demand (L/day)"] - mesh["Estimated Outage Population"] * mesh["Per Capita Water Demand (L/person/day)"]).abs()
    check(bool(identity.dropna().le(1e-8).all()), "mesh_demand_identity", {"max_error": float(identity.max(skipna=True))}, checks, failures)
    no_report = mesh["Outage Observation Status"].eq("not_reported")
    check(bool(mesh.loc[no_report, "Estimated Outage Population"].isna().all() and mesh.loc[no_report, "Estimated Water Demand (L/day)"].isna().all()), "unreported_remains_missing", {"rows": int(no_report.sum())}, checks, failures)
    reported_zero = mesh["Outage Observation Status"].eq("reported_zero")
    check(bool(mesh.loc[reported_zero, "Estimated Water Demand (L/day)"].eq(0).all()), "reported_zero_is_zero", {"rows": int(reported_zero.sum())}, checks, failures)

    municipal = pd.read_parquet(ROOT / "data/processed/municipality_outage_demand_scenarios_preprocessed.parquet")
    pivot = municipal[municipal["Demand Scenario"].eq("minimum")].pivot_table(
        index=["Reporting Municipality Code", "Reporting Municipality Name"],
        columns="Outage Population Scenario", values="Estimated Outage Population", aggfunc="first",
    ).dropna()
    ordered = (
        pivot["lower_one_person_per_household"] <= pivot["proportional_central"]
    ) & (
        pivot["proportional_central"] <= pivot["upper_p90_household_size"]
    )
    check(bool(ordered.all()), "population_scenario_order", {"municipalities_checked": len(ordered)}, checks, failures)

    water = pd.read_parquet(ROOT / "data/processed/emergency_water_points_network_access_preprocessed.parquet")
    water_location = water["Location Resolution Status"].value_counts().to_dict()
    check(water_location == {"unmatched": 19, "matched_exact_2012_facility": 10, "matched_exact_candidate_unique_geometry": 7}, "water_point_location_status", water_location, checks, failures)
    check(int(water["Network Snap Accepted"].fillna(False).sum()) == 17 and bool(water.loc[water["Network Snap Accepted"].fillna(False), "Network Snap Distance (m)"].le(250).all()), "water_point_network_threshold", {}, checks, failures)

    shelter = pd.read_parquet(ROOT / "data/processed/shelter_water_demand_network_access_preprocessed.parquet")
    unique_shelter = shelter.drop_duplicates("Shelter Number")
    shelter_location = unique_shelter["Location Resolution Status"].value_counts().to_dict()
    check(shelter_location == {"unmatched": 24, "matched_exact_2012_facility": 12, "matched_exact_candidate_unique_geometry": 5}, "shelter_location_status", shelter_location, checks, failures)
    check(int(unique_shelter["Network Snap Accepted"].fillna(False).sum()) == 17 and bool(unique_shelter.loc[unique_shelter["Network Snap Accepted"].fillna(False), "Network Snap Distance (m)"].le(250).all()), "shelter_network_threshold", {}, checks, failures)
    shelter_identity = (shelter["Estimated Shelter Water Demand (L/day)"] - shelter["Evacuee People"] * shelter["Per Capita Water Demand (L/person/day)"]).abs()
    check(bool(shelter_identity.le(1e-8).all() and shelter["Shelter Demand Accounting Status"].eq("separate_not_added_to_resident_demand").all()), "shelter_demand_separate", {}, checks, failures)

    restrictions = pd.read_parquet(ROOT / "data/processed/road_restriction_edge_matches_preprocessed.parquet")
    methods = restrictions["Road Edge Match Method"]
    distances = restrictions["Road Edge Match Distance (m)"]
    threshold_ok = (
        distances[methods.eq("line_buffer_50m")].le(50).all()
        and distances[methods.eq("point_nearest_100m")].le(100).all()
        and distances[methods.eq("nearest_edge_250m_fallback")].le(250).all()
        and distances[methods.eq("none")].isna().all()
    )
    check(bool(threshold_ok), "restriction_match_thresholds", restrictions["Road Edge Match Status"].value_counts().to_dict(), checks, failures)
    check(restrictions["Restriction Observation ID"].nunique() == 680, "all_restriction_observations_retained", {"unique": restrictions["Restriction Observation ID"].nunique()}, checks, failures)

    parameters = pd.read_parquet(ROOT / "data/processed/emergency_water_scenario_parameters_preprocessed.parquet")
    parameter_type = pq.read_schema(ROOT / "data/processed/emergency_water_scenario_parameters_preprocessed.parquet").field("Parameter Value").type
    parameter_is_string = pa.types.is_string(parameter_type) or pa.types.is_large_string(parameter_type)
    check(parameter_is_string and parameters["Parameter Name"].nunique() == 12, "parameter_long_format", {"parameters": parameters["Parameter Name"].nunique(), "arrow_type": str(parameter_type)}, checks, failures)

    manifest_rows = []
    for source_text, output_text in SOURCES.items():
        source = (ROOT / source_text).resolve()
        output = ROOT / output_text
        manifest_rows.append({
            "source_path": source_text,
            "source_sha256": sha256_file(source),
            "source_bytes": source.stat().st_size,
            "output_path": output_text,
            "output_rows": pq.read_metadata(output).num_rows,
            "output_columns": pq.read_metadata(output).num_columns,
        })
    output_dir = ROOT / "data/exp/data-preprocessing"
    with (output_dir / "round2_source_manifest.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(manifest_rows[0]))
        writer.writeheader()
        writer.writerows(manifest_rows)
    report = {"status": "passed" if not failures else "failed", "checks": checks, "failures": failures}
    (output_dir / "round2_validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Validation status: {report['status']}")
    print(f"Checks passed: {sum(bool(item['passed']) for item in checks)}/{len(checks)}")
    if failures:
        raise SystemExit("; ".join(failures))


if __name__ == "__main__":
    main()
