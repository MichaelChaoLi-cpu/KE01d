#!/usr/bin/env python3
"""Merge confirmed integration decisions into the authoritative decisions file."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / "data/exp/data-preprocessing/decisions.json"
GENERATOR_DECISIONS = ROOT / "data/exp/data-preprocessing/integration_generator_decisions.json"


def variable(
    name: str,
    *,
    readable: str | None = None,
    full: str | None = None,
    final: bool = True,
    operations: list[str] | None = None,
) -> dict[str, object]:
    readable_name = readable or name
    return {
        "original_name": name,
        "readable_name": readable_name,
        "full_name": full or readable_name.replace(" ID", " Identifier"),
        "is_final_variable": "yes" if final else "no",
        "preprocessing": operations or [],
    }


def dataset(output: str, script: str, variables: list[dict[str, object]]) -> dict[str, object]:
    return {"output": output, "script": script, "variables": variables}


def main() -> None:
    decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))

    external: dict[str, dict[str, object]] = {
        "../KE01b/data/processed/kumamoto_administrative_areas_preprocessed.parquet": dataset(
            "data/processed/kumamoto_administrative_areas_preprocessed.parquet",
            "src/preprocessing/preprocess_kumamoto_administrative_areas.py",
            [
                variable("Municipality Code"),
                variable("Prefecture Name", final=False),
                variable("District Name", final=False),
                variable("Municipality Name"),
                variable("Ward Name", final=False),
                variable("Municipality Label"),
                variable("Geometry", operations=["preserve_geoparquet_metadata"]),
            ],
        ),
        "../KE01b/data/processed/kumamoto_population_mesh_125m_preprocessed.parquet": dataset(
            "data/processed/kumamoto_population_mesh_125m_preprocessed.parquet",
            "src/preprocessing/preprocess_kumamoto_population_mesh_125m.py",
            [
                variable("Mesh Code"),
                variable("Geometry", operations=["preserve_geoparquet_metadata"]),
                variable("Disclosure Group Code"),
                variable("Disclosure Group Size"),
                variable("Disclosure Status"),
                variable("Aggregation Destination Mesh Code", final=False),
                variable("Aggregated Source Mesh Codes", final=False),
                variable("Total Population"),
                variable("Total Households"),
                variable("General Households"),
            ],
        ),
        "../KE01b/data/processed/kumamoto_population_disclosure_groups_preprocessed.parquet": dataset(
            "data/processed/kumamoto_population_disclosure_groups_preprocessed.parquet",
            "src/preprocessing/preprocess_kumamoto_population_disclosure_groups.py",
            [
                variable(name, operations=["preserve_geoparquet_metadata"] if name == "Geometry" else [])
                for name in [
                    "Disclosure Group Code", "Geometry", "Disclosure Group Size",
                    "Suppressed Source Mesh Count", "Total Population", "Total Households",
                    "General Households", "Population Age 65+", "Population Age 75+",
                    "Population Age 85+", "One-Person Households",
                    "Households with Member Age 65+", "Older Single-Person Households",
                    "Older Couple Households", "Population Age 65+ Share",
                    "Population Age 75+ Share", "Population Age 85+ Share",
                    "Older Single-Person Household Share", "Older Couple Household Share",
                ]
            ],
        ),
        "../KE01b/data/processed/kumamoto_population_mesh_network_access_preprocessed.parquet": dataset(
            "data/processed/kumamoto_population_mesh_network_access_preprocessed.parquet",
            "src/preprocessing/preprocess_kumamoto_population_mesh_network_access.py",
            [
                variable(name, operations=["preserve_geoparquet_metadata"] if name == "Geometry" else [])
                for name in [
                    "Mesh Code", "Geometry", "Analysis Unit ID", "Demand Node ID",
                    "Network Snap Distance (m)", "Network Snap Accepted",
                    "Access Road Edge ID", "Access Edge Fraction",
                ]
            ],
        ),
        "../KE01b/data/processed/kumamoto_population_group_network_access_preprocessed.parquet": dataset(
            "data/processed/kumamoto_population_group_network_access_preprocessed.parquet",
            "src/preprocessing/preprocess_kumamoto_population_group_network_access.py",
            [
                variable(name, operations=["preserve_geoparquet_metadata"] if name == "Geometry" else [])
                for name in [
                    "Disclosure Group Code", "Analysis Unit ID", "Representative Mesh Code",
                    "Geometry", "Demand Node ID", "Network Snap Distance (m)",
                    "Network Snap Accepted", "Access Road Edge ID", "Access Edge Fraction",
                ]
            ],
        ),
        "../KE01b/data/processed/kumamoto_routable_road_edges_preprocessed.parquet": dataset(
            "data/processed/kumamoto_routable_road_edges_preprocessed.parquet",
            "src/preprocessing/preprocess_kumamoto_routable_road_edges.py",
            [
                variable(name, operations=["preserve_geoparquet_metadata"] if name == "Geometry" else [])
                for name in [
                    "Road Edge ID", "Road Section ID", "From Node ID", "To Node ID",
                    "Network Component ID", "Road Length (m)", "Assumed Speed (km/h)",
                    "Baseline Edge Travel Time (min)", "Hazard Exposure Class",
                    "Emergency Route Membership", "Road Available",
                    "Network Analysis Eligible", "Route ID", "Route Name", "Road Category",
                    "Road State", "Vertical Level", "Width Category", "Toll Category",
                    "Secondary Mesh Code", "Geometry",
                ]
            ],
        ),
        "../KE01c/data/results/derived/staging_site_candidates.parquet": dataset(
            "data/processed/kumamoto_staging_site_candidates_preprocessed.parquet",
            "src/preprocessing/preprocess_kumamoto_staging_site_candidates.py",
            [
                variable(
                    name,
                    operations=["reproject:EPSG:6670->EPSG:6668"] if name == "Geometry" else (
                        ["to_nullable_boolean"] if name == "Network Snap Accepted" else []
                    ),
                )
                for name in [
                    "Candidate Staging Site ID", "Candidate Staging Site Type",
                    "Candidate Staging Site Name", "Candidate Source Status",
                    "Staging Source Priority", "Geometry", "Access Mesh Code",
                    "Staging Demand Node ID", "Staging Access Network Snap Distance (m)",
                    "Network Snap Accepted", "Staging-to-Mesh Distance (m)",
                    "Total Population", "Candidate Network Eligible",
                    "Screened Staging Candidate",
                ]
            ],
        ),
        "../KE01b/data/processed/kumamoto_fire_stations_2012_preprocessed.parquet": dataset(
            "data/processed/kumamoto_fire_stations_2012_preprocessed.parquet",
            "src/preprocessing/preprocess_kumamoto_fire_stations_2012.py",
            [
                variable(name, operations=["preserve_geoparquet_metadata"] if name == "Geometry" else [])
                for name in [
                    "Fire Facility Name", "Municipality Code", "Fire Facility Type Code",
                    "Address", "Geometry", "Fire Facility Type", "Candidate Dispatch Base",
                ]
            ],
        ),
    }

    p21: dict[str, dict[str, object]] = {
        "data/raw/reference/mlit_p21_2012/P21-12_43_GML.zip::P21-12a_43.shp": dataset(
            "data/processed/kumamoto_water_supply_areas_2010_preprocessed.parquet",
            "src/preprocessing/preprocess_p21_water_supply_areas.py",
            [
                variable("P21A_001", readable="Water Utility Operator", operations=["strip_whitespace"]),
                variable("P21A_002", readable="Water Service Name", operations=["strip_whitespace"]),
                variable("P21A_003", readable="Water Service Type Code", operations=["to_numeric"]),
                variable("P21A_004", readable="Served Population", operations=["to_numeric", "zero_to_missing"]),
                variable("P21A_005", readable="Maximum Daily Supply (m3/day)", operations=["to_numeric", "zero_to_missing"]),
                variable("検査ID", readable="P21 Inspection ID", full="P21 Inspection Identifier", final=False, operations=["to_numeric"]),
                variable("Geometry", operations=["reproject:EPSG:4612->EPSG:6668"]),
                variable("__source_reference_year", readable="Source Reference Year", operations=["fill_constant:2010"]),
                variable("__dataset_edition_year", readable="Dataset Edition Year", operations=["fill_constant:2012"]),
                variable("__historical_capacity_only", readable="Historical Capacity Only", operations=["fill_constant:True"]),
            ],
        ),
        "data/raw/reference/mlit_p21_2012/P21-12_43_GML.zip::P21-12b_43.shp": dataset(
            "data/processed/kumamoto_water_treatment_facilities_2010_preprocessed.parquet",
            "src/preprocessing/preprocess_p21_water_treatment_facilities.py",
            [
                variable("P21B_001", readable="Water Utility Operator", operations=["strip_whitespace"]),
                variable("P21B_002", readable="Water Service Name", operations=["strip_whitespace"]),
                variable("P21B_003", readable="Water Treatment Facility Name", operations=["strip_whitespace"]),
                variable("P21B_004", readable="Maximum Daily Supply (m3/day)", operations=["to_numeric", "zero_to_missing"]),
                variable("検査ID", readable="P21 Inspection ID", full="P21 Inspection Identifier", final=False, operations=["to_numeric"]),
                variable("Geometry", operations=["reproject:EPSG:4612->EPSG:6668"]),
                variable("__source_reference_year", readable="Source Reference Year", operations=["fill_constant:2010"]),
                variable("__dataset_edition_year", readable="Dataset Edition Year", operations=["fill_constant:2012"]),
                variable("__historical_capacity_only", readable="Historical Capacity Only", operations=["fill_constant:True"]),
            ],
        ),
    }

    decisions["datasets"].update(external)
    decisions["datasets"].update(p21)
    DECISIONS.write_text(json.dumps(decisions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    GENERATOR_DECISIONS.write_text(
        json.dumps({"datasets": external}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Authoritative datasets: {len(decisions['datasets'])}")
    print(
        "Selected variables: "
        + str(sum(len(item["variables"]) for item in decisions["datasets"].values()))
    )
    print(f"Generator subset datasets: {len(external)}")


if __name__ == "__main__":
    main()
