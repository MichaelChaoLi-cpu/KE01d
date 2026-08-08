#!/usr/bin/env python3
"""Merge confirmed second-round preprocessing decisions into the authoritative record."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / "data/exp/data-preprocessing/decisions.json"


def variables(names: list[str], operations: dict[str, list[str]] | None = None) -> list[dict[str, object]]:
    operations = operations or {}
    return [
        {
            "original_name": name,
            "readable_name": name,
            "full_name": name.replace(" ID", " Identifier"),
            "is_final_variable": "yes",
            "preprocessing": operations.get(name, []),
        }
        for name in names
    ]


def specification(output: str, script: str, names: list[str], operations: dict[str, list[str]] | None = None) -> dict[str, object]:
    return {"output": output, "script": script, "variables": variables(names, operations)}


def main() -> None:
    payload = json.loads(DECISIONS.read_text(encoding="utf-8"))
    datasets = payload["datasets"]

    datasets["../KE01b/data/processed/kumamoto_routable_road_nodes_preprocessed.parquet"] = specification(
        "data/processed/kumamoto_routable_road_nodes_preprocessed.parquet",
        "src/preprocessing/preprocess_kumamoto_routable_road_nodes.py",
        ["Network Node ID", "Network Component ID", "Network Analysis Eligible", "Vertical Level", "Geometry"],
        {"Geometry": ["preserve_geoparquet_metadata"]},
    )
    datasets["../KE01b/data/processed/kumamoto_dispatch_base_network_access_preprocessed.parquet"] = specification(
        "data/processed/kumamoto_dispatch_base_network_access_preprocessed.parquet",
        "src/preprocessing/preprocess_kumamoto_dispatch_base_network_access.py",
        ["Fire Facility Name", "Municipality Code", "Fire Facility Type Code", "Address", "Geometry", "Fire Facility Type", "Candidate Dispatch Base", "Dispatch Base Node ID", "Network Snap Distance (m)", "Network Snap Accepted", "Access Road Edge ID", "Access Edge Fraction"],
        {"Geometry": ["preserve_geoparquet_metadata"]},
    )

    derived = {
        "derived:reporting_unit_municipality_crosswalk": specification(
            "data/processed/reporting_unit_municipality_crosswalk_preprocessed.parquet",
            "src/preprocessing/preprocess_reporting_unit_municipality_crosswalk.py",
            ["Reporting Unit Type", "Reporting Unit", "Reporting Prefecture", "Reporting Municipality Code", "Reporting Municipality Name", "Municipality Match Status", "In Kumamoto Study Area", "Joint Operator Area Status"],
        ),
        "derived:kumamoto_reporting_municipalities": specification(
            "data/processed/kumamoto_reporting_municipalities_preprocessed.parquet",
            "src/preprocessing/preprocess_kumamoto_reporting_municipalities.py",
            ["Reporting Municipality Code", "Reporting Municipality Name", "Constituent Administrative Unit Count", "Kumamoto City Ward Dissolved", "Geometry"],
            {"Geometry": ["dissolve_kumamoto_city_wards", "preserve_geoparquet_metadata"]},
        ),
        "derived:municipality_outage_demand_scenarios": specification(
            "data/processed/municipality_outage_demand_scenarios_preprocessed.parquet",
            "src/preprocessing/preprocess_municipality_outage_demand_scenarios.py",
            ["Reporting Municipality Code", "Reporting Municipality Name", "Geometry", "Report Number", "Water Status Timestamp", "Maximum Outage Households", "Current Outage Households", "Outage Observation Status", "Tanker Total", "MLIT Tankers", "JWWA Tankers", "SDF Tankers", "Municipality Total Population", "Municipality Total Households", "Outage Household Ratio", "Outage Population Scenario", "Estimated Outage Population", "Demand Scenario", "Per Capita Water Demand (L/person/day)", "Estimated Water Demand (L/day)"],
        ),
        "derived:population_mesh_outage_demand_scenarios": specification(
            "data/processed/population_mesh_outage_demand_scenarios_preprocessed.parquet",
            "src/preprocessing/preprocess_population_mesh_outage_demand_scenarios.py",
            ["Mesh Code", "Reporting Municipality Code", "Reporting Municipality Name", "Spatial Join Status", "Geometry", "Total Population", "Total Households", "Municipality Total Households", "Municipality Household Share", "Outage Snapshot Time", "Current Outage Households", "Outage Observation Status", "Outage Household Ratio", "Outage Population Scenario", "Estimated Outage Population", "Demand Scenario", "Per Capita Water Demand (L/person/day)", "Estimated Water Demand (L/day)"],
        ),
        "derived:emergency_water_points_network_access": specification(
            "data/processed/emergency_water_points_network_access_preprocessed.parquet",
            "src/preprocessing/preprocess_emergency_water_points_network_access.py",
            ["Municipality", "Water Point Name", "Valid From Date", "Valid To Date", "Opening Time", "Closing Time", "Allocation Basis", "Allocation Limit (L)", "Water Type", "Source Status Time", "Latitude", "Longitude", "Geometry", "Location Resolution Status", "Location Resolution Source", "Location Match Candidate Record Count", "Location Match Candidate Geometry Count", "Water Point Node ID", "Network Snap Distance (m)", "Network Snap Accepted", "Access Road Edge ID", "Access Edge Fraction"],
        ),
        "derived:shelter_water_demand_network_access": specification(
            "data/processed/shelter_water_demand_network_access_preprocessed.parquet",
            "src/preprocessing/preprocess_shelter_water_demand_network_access.py",
            ["Municipality", "Shelter Number", "Shelter Name", "District", "Maximum Capacity", "Evacuee Households", "Evacuee People", "Water Status", "Electricity Status", "Air Conditioning Status", "Toilet Count", "Portable Toilet Count", "Snapshot Time", "Latitude", "Longitude", "Geometry", "Location Resolution Status", "Location Resolution Source", "Location Match Candidate Record Count", "Location Match Candidate Geometry Count", "Shelter Node ID", "Network Snap Distance (m)", "Network Snap Accepted", "Access Road Edge ID", "Access Edge Fraction", "Demand Scenario", "Per Capita Water Demand (L/person/day)", "Estimated Shelter Water Demand (L/day)", "Shelter Demand Accounting Status"],
        ),
        "derived:road_restriction_edge_matches": specification(
            "data/processed/road_restriction_edge_matches_preprocessed.parquet",
            "src/preprocessing/preprocess_road_restriction_edge_matches.py",
            ["Restriction Observation ID", "Snapshot Time", "Route Name", "Restriction Status", "Restriction Reason", "Geometry", "Matched Road Edge ID", "Road Edge Match Distance (m)", "Route Name Agreement", "Road Edge Match Candidate Count", "Road Edge Match Method", "Road Edge Match Status"],
        ),
        "derived:emergency_water_scenario_parameters": specification(
            "data/processed/emergency_water_scenario_parameters_preprocessed.parquet",
            "src/preprocessing/preprocess_emergency_water_scenario_parameters.py",
            ["Parameter Name", "Scenario Level", "Parameter Value", "Parameter Unit", "Evidence Class", "Evidence Source", "Parameter Notes"],
        ),
    }
    datasets.update(derived)
    DECISIONS.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Datasets: {len(datasets)}")
    print(f"Selected variables: {sum(len(item['variables']) for item in datasets.values())}")


if __name__ == "__main__":
    main()
