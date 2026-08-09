#!/usr/bin/env python3
"""Marginal Protection Gains from Additional Tankers.

Plan: Compare remaining unmet minimum water and the interval-average protected-
population gain per added tanker at 0, 1, 5, 10, and 20 vehicles under matched
500, 1,000, and 2,000 m allocation catchments.
Framework: AnaSOP Sections 5-7 unmet-water U_n and marginal-gain Delta P_n
equations using the central affected-population estimate, 3 L/person/day,
no modeled road closures, and the route-constrained resident allocation ledger.
The 2,000 m catchment is an extended allocation diagnostic, not a walking
standard.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import figure_scenario_based_tanker_and_temporary_water_point_allocation as allocation
from _figure_style import (
    BLACK,
    GREEN,
    VERMILLION,
    YELLOW,
    annotation_box,
    panel_label,
    set_theme,
    style_cartesian_axis,
)


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = (
    ROOT
    / "data/results/figures/Figure_marginal_protection_gains_from_additional_tankers.png"
)
AUDIT_PATH = ROOT / "data/exp/marginal_protection_solver_audit.json"
CURVE_PATH = ROOT / "data/exp/marginal_protection_resource_curve.csv"
FLEET_SIZES = [0, 1, 5, 10, 20]
CATCHMENT_SPECS = [
    ("500 m", 500.0),
    ("1,000 m", 1_000.0),
    ("2,000 m", 2_000.0),
]
COLORS = {
    "500 m": GREEN,
    "1,000 m": YELLOW,
    "2,000 m": VERMILLION,
}
MARKERS = {
    "500 m": "o",
    "1,000 m": "s",
    "2,000 m": "^",
}
LINESTYLES = {
    "500 m": "-",
    "1,000 m": (0, (4.0, 2.0)),
    "2,000 m": (0, (1.2, 1.8)),
}


def load_scenarios() -> tuple[
    dict[str, allocation.ScenarioInputs],
    float,
]:
    parameters = pd.read_parquet(allocation.PARAMETERS)
    nodes = gpd.read_parquet(
        allocation.ROAD_NODES, columns=["Network Node ID", "Geometry"]
    )
    edges = pd.read_parquet(
        allocation.ROAD_EDGES,
        columns=[
            "Road Edge ID",
            "From Node ID",
            "To Node ID",
            "Road Length (m)",
            "Baseline Edge Travel Time (min)",
            "Road Available",
            "Network Analysis Eligible",
        ],
    )
    demand = gpd.read_parquet(
        allocation.MESH_DEMAND,
        columns=[
            "Mesh Code",
            "Geometry",
            "Outage Population Scenario",
            "Demand Scenario",
            "Estimated Outage Population",
            "Estimated Water Demand (L/day)",
        ],
    )
    access = pd.read_parquet(allocation.MESH_ACCESS)
    water = gpd.read_parquet(allocation.WATER_POINTS)
    staging = gpd.read_parquet(allocation.STAGING)
    older_weight = allocation.older_priority_weights()

    scenarios: dict[str, allocation.ScenarioInputs] = {}
    for label, access_distance_m in CATCHMENT_SPECS:
        scenarios[label] = allocation.prepare_scenario(
            label,
            set(),
            None,
            nodes,
            edges,
            demand,
            access,
            water,
            staging,
            parameters,
            older_weight,
            access_distance_m=access_distance_m,
        )

    total_demand = float(
        demand.loc[
            demand["Outage Population Scenario"].eq("proportional_central")
            & demand["Demand Scenario"].eq("minimum")
            & demand["Estimated Water Demand (L/day)"].gt(0),
            "Estimated Water Demand (L/day)",
        ].sum()
    )
    for label, scenario in scenarios.items():
        scenario_demand = float(
            scenario.units["Estimated Water Demand (L/day)"].sum()
        )
        if not np.isclose(total_demand, scenario_demand, rtol=0, atol=1e-6):
            raise ValueError(f"Allocation denominator omits demand for {label}")
    return scenarios, total_demand


def signature_digest(
    scenario: allocation.ScenarioInputs,
    result: allocation.AllocationResult,
) -> tuple[dict[str, object], str]:
    signature = allocation.allocation_signature(scenario, result)
    encoded = json.dumps(
        signature, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    summary = {
        "delivery_liters": signature["delivery_liters"],
        "fleet_used": signature["fleet_used"],
        "trips_used": signature["trips_used"],
        "temporary_sites": signature["temporary_sites"],
        "selected_site_ids": signature["selected_site_ids"],
    }
    return summary, hashlib.sha256(encoded).hexdigest()


def write_audit(records: list[dict[str, object]], status: str) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": status,
        "model": "capacity-first resident allocation",
        "solver_acceptance": (
            "valid incumbent plus direct constraint validation and either "
            "MIP gap <= 0.01 or physical-bound shortfall <= 0.002"
        ),
        "rerun_rule": (
            "independent rerun must reproduce delivered water within 1e-6 L; "
            "configuration hashes are retained as diagnostics"
        ),
        "thread_convention": "single thread",
        "runs": records,
    }
    AUDIT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def calculate_resource_curve() -> tuple[pd.DataFrame, list[dict[str, object]]]:
    scenarios, total_demand = load_scenarios()
    records: list[dict[str, float | int | str]] = []
    audit_records: list[dict[str, object]] = []
    write_audit(audit_records, "running")
    for catchment, scenario in scenarios.items():
        accessible_units = scenario.arcs["Unit Index"].drop_duplicates().to_numpy()
        accessible_demand = float(
            scenario.units.iloc[accessible_units][
                "Estimated Water Demand (L/day)"
            ].sum()
        )
        records.append(
            {
                "Fleet Size": 0,
                "Catchment": catchment,
                "Delivered Water (L/day)": 0.0,
                "Protected Share": 0.0,
                "Unmet Water (L/day)": total_demand,
                "Access Ceiling": accessible_demand / total_demand,
            }
        )
        for fleet_size in FLEET_SIZES[1:]:
            started = time.perf_counter()
            result = allocation.solve_allocation(
                scenario, fleet_size, refine=False
            )
            repeat_result = allocation.solve_allocation(
                scenario, fleet_size, refine=False
            )
            allocation.validate_solution(scenario, result, fleet_size)
            allocation.validate_solution(scenario, repeat_result, fleet_size)
            first_summary, first_hash = signature_digest(scenario, result)
            repeat_summary, repeat_hash = signature_digest(
                scenario, repeat_result
            )
            objective_agreement = bool(
                np.isclose(
                    result.delivery_liters,
                    repeat_result.delivery_liters,
                    rtol=0,
                    atol=1e-6,
                )
            )
            if not objective_agreement:
                raise RuntimeError(
                    "Independent reruns disagree on delivered water: "
                    f"catchment={catchment}; fleet={fleet_size}"
                )
            audit_records.append(
                {
                    "catchment": catchment,
                    "fleet_size": fleet_size,
                    "elapsed_seconds_for_two_runs": round(
                        time.perf_counter() - started, 3
                    ),
                    "direct_constraint_validation": "passed",
                    "aggregate_objective_agreement": objective_agreement,
                    "exact_configuration_agreement": first_hash == repeat_hash,
                    "first_run": {
                        **first_summary,
                        "configuration_sha256": first_hash,
                        "solver_stages": list(result.solver_audit),
                    },
                    "repeat_run": {
                        **repeat_summary,
                        "configuration_sha256": repeat_hash,
                        "solver_stages": list(repeat_result.solver_audit),
                    },
                }
            )
            write_audit(audit_records, "running")
            records.append(
                {
                    "Fleet Size": fleet_size,
                    "Catchment": catchment,
                    "Delivered Water (L/day)": result.delivery_liters,
                    "Protected Share": result.delivery_liters / total_demand,
                    "Unmet Water (L/day)": total_demand - result.delivery_liters,
                    "Access Ceiling": accessible_demand / total_demand,
                }
            )
            print(
                "Resource-curve optimization complete: "
                f"catchment={catchment}; fleet={fleet_size}; "
                f"validated=yes; rerun_objective_agreement=yes"
            )

    curve = pd.DataFrame(records)
    curve["Marginal Gain (pp/vehicle)"] = np.nan
    for catchment, index in curve.groupby("Catchment", sort=False).groups.items():
        ordered = curve.loc[index].sort_values("Fleet Size")
        gain = (
            ordered["Protected Share"].diff()
            / ordered["Fleet Size"].diff()
            * 100.0
        )
        curve.loc[ordered.index, "Marginal Gain (pp/vehicle)"] = gain.to_numpy()
        if np.any(np.diff(ordered["Protected Share"].to_numpy()) < -1e-9):
            raise ValueError(f"Protected share is not monotonic for {catchment}")
    curve = curve.sort_values(["Catchment", "Fleet Size"]).reset_index(drop=True)
    CURVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    curve.to_csv(CURVE_PATH, index=False)
    write_audit(audit_records, "complete")
    return curve, audit_records


def main() -> None:
    curve, audit_records = calculate_resource_curve()
    if len(audit_records) != len(CATCHMENT_SPECS) * (len(FLEET_SIZES) - 1):
        raise ValueError("Solver audit does not cover every nonzero curve point")
    set_theme()
    fig, axes = plt.subplots(2, 1, figsize=(8.3, 8.4))
    fig.subplots_adjust(left=0.13, right=0.96, top=0.96, bottom=0.09, hspace=0.33)

    for catchment, _ in CATCHMENT_SPECS:
        selected = curve.loc[curve["Catchment"].eq(catchment)].sort_values(
            "Fleet Size"
        )
        style = {
            "color": COLORS[catchment],
            "marker": MARKERS[catchment],
            "linestyle": LINESTYLES[catchment],
            "linewidth": 2.3,
            "markersize": 6.2,
            "markeredgecolor": BLACK,
            "markeredgewidth": 0.65,
            "label": catchment,
        }
        axes[0].plot(
            selected["Fleet Size"],
            selected["Unmet Water (L/day)"] / 1000.0,
            **style,
        )
        marginal = selected.dropna(subset=["Marginal Gain (pp/vehicle)"])
        axes[1].plot(
            marginal["Fleet Size"],
            marginal["Marginal Gain (pp/vehicle)"],
            **style,
        )

    total_demand_m3 = float(curve["Unmet Water (L/day)"].max() / 1000.0)
    axes[0].set_ylabel("Remaining unmet minimum water (m³/day)")
    axes[0].set_ylim(0, total_demand_m3 * 1.025)
    axes[0].legend(
        title="Allocation catchment",
        loc="upper right",
        frameon=True,
        fontsize=8.2,
        title_fontsize=8.7,
        labelspacing=0.55,
        borderpad=0.7,
    )
    annotation_box(
        axes[0],
        "Central affected population\n3 L/person/day\nNo modeled road closures",
        x=0.025,
        y=0.045,
        fontsize=7.8,
    )

    axes[1].set_ylabel(
        "Average marginal protection gain\n(percentage points/vehicle)"
    )
    axes[1].set_ylim(bottom=0)

    for label, ax in zip("ab", axes, strict=True):
        ax.set_xlabel("Available tankers")
        ax.set_xticks(FLEET_SIZES)
        ax.set_xlim(-0.4, 20.4)
        style_cartesian_axis(ax)
        panel_label(ax, label, x=-0.08, y=1.045)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    for catchment, _ in CATCHMENT_SPECS:
        selected = curve.loc[curve["Catchment"].eq(catchment)].sort_values(
            "Fleet Size"
        )
        unmet = ", ".join(
            f"{int(row['Fleet Size'])}={row['Unmet Water (L/day)'] / 1000:.3f}"
            for _, row in selected.iterrows()
        )
        gains = ", ".join(
            f"{int(row['Fleet Size'])}={row['Marginal Gain (pp/vehicle)']:.3f}"
            for _, row in selected.dropna(
                subset=["Marginal Gain (pp/vehicle)"]
            ).iterrows()
        )
        access_ceiling = float(selected["Access Ceiling"].iloc[0])
        print(
            f"{catchment} access ceiling={access_ceiling:.3%}; "
            f"unmet m3/day: {unmet}; marginal pp/vehicle: {gains}"
        )
    print(f"Saved: {OUTPUT_PATH.relative_to(ROOT)}")
    print(f"Saved curve data: {CURVE_PATH.relative_to(ROOT)}")
    print(f"Saved solver audit: {AUDIT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
