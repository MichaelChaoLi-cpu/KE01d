#!/usr/bin/env python3
"""Marginal Protection Gains from Additional Tankers.

Plan: Trace fully protected resident share, remaining minimum-water gap, and
incremental protection per added tanker at 0, 1, 5, 10, and 20 vehicles under
baseline roads, matched-restriction closure stress testing, and exhaustive
worst single announced-point failure.
Framework: AnaSOP Sections 5-7 protected-share P_n, unmet-water U_n, and
marginal-gain Delta P_n equations using the central outage-population estimate,
3 L/person/day, 500 m access arcs, and the route-constrained resident ledger.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.ticker import PercentFormatter

import figure_scenario_based_tanker_and_temporary_water_point_allocation as allocation


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT / "data/results/figures/Figure_marginal_protection_gains_from_additional_tankers.png"
FLEET_SIZES = [0, 1, 5, 10, 20]
STATE_ORDER = [
    "Baseline roads",
    "Matched restrictions closed",
    "Worst single-point failure",
]
COLORS = {
    "Baseline roads": "#087e8b",
    "Matched restrictions closed": "#d97706",
    "Worst single-point failure": "#7b2cbf",
}
MARKERS = {
    "Baseline roads": "o",
    "Matched restrictions closed": "s",
    "Worst single-point failure": "^",
}


def load_scenarios() -> tuple[
    allocation.ScenarioInputs,
    allocation.ScenarioInputs,
    float,
]:
    parameters = pd.read_parquet(allocation.PARAMETERS)
    nodes = gpd.read_parquet(
        allocation.ROAD_NODES, columns=["Network Node ID", "Geometry"]
    )
    edges = pd.read_parquet(
        allocation.ROAD_EDGES,
        columns=[
            "Road Edge ID", "From Node ID", "To Node ID", "Road Length (m)",
            "Baseline Edge Travel Time (min)", "Road Available",
            "Network Analysis Eligible",
        ],
    )
    demand = gpd.read_parquet(
        allocation.MESH_DEMAND,
        columns=[
            "Mesh Code", "Geometry", "Outage Population Scenario", "Demand Scenario",
            "Estimated Outage Population", "Estimated Water Demand (L/day)",
        ],
    )
    access = pd.read_parquet(allocation.MESH_ACCESS)
    water = gpd.read_parquet(allocation.WATER_POINTS)
    staging = gpd.read_parquet(allocation.STAGING)
    restrictions = pd.read_parquet(
        allocation.RESTRICTIONS,
        columns=["Matched Road Edge ID", "Road Edge Match Status"],
    )
    closed_edges = set(
        restrictions.loc[
            restrictions["Road Edge Match Status"].eq("matched_primary"),
            "Matched Road Edge ID",
        ].dropna().astype(str)
    )
    older_weight = allocation.older_priority_weights()
    baseline = allocation.prepare_scenario(
        "Baseline roads", set(), None, nodes, edges, demand, access, water,
        staging, parameters, older_weight
    )
    disruption = allocation.prepare_scenario(
        "Matched restrictions closed", closed_edges, None, nodes, edges, demand,
        access, water, staging, parameters, older_weight
    )
    total_demand = float(
        demand.loc[
            demand["Outage Population Scenario"].eq("proportional_central")
            & demand["Demand Scenario"].eq("minimum")
            & demand["Estimated Water Demand (L/day)"].gt(0),
            "Estimated Water Demand (L/day)",
        ].sum()
    )
    scenario_demand = float(
        baseline.units["Estimated Water Demand (L/day)"].sum()
    )
    if not np.isclose(total_demand, scenario_demand, rtol=0, atol=1e-6):
        raise ValueError("Allocation denominator omits positive resident demand")
    return baseline, disruption, total_demand


def worst_failure_result(
    baseline: allocation.ScenarioInputs, fleet_size: int
) -> tuple[allocation.AllocationResult, str]:
    existing_indices = np.flatnonzero(
        ~baseline.sites["Temporary Site"].to_numpy(bool)
    )
    worst_result: allocation.AllocationResult | None = None
    worst_name = ""
    for site_index in existing_indices:
        scenario = allocation.remove_announced_site(baseline, int(site_index))
        name = str(baseline.sites.iloc[int(site_index)]["Site Name"])
        result = allocation.solve_allocation(
            scenario, fleet_size, failed_point=name, refine=False
        )
        if worst_result is None or result.delivery_liters < worst_result.delivery_liters:
            worst_result = result
            worst_name = name
    if worst_result is None:
        raise ValueError("No announced point was available for failure screening")
    return worst_result, worst_name


def calculate_resource_curve() -> pd.DataFrame:
    baseline, disruption, total_demand = load_scenarios()
    records = []
    for state in STATE_ORDER:
        records.append(
            {
                "Fleet Size": 0,
                "State": state,
                "Delivered Water (L/day)": 0.0,
                "Protected Share": 0.0,
                "Unmet Water (L/day)": total_demand,
                "Worst Failed Point": None,
            }
        )
    for fleet_size in FLEET_SIZES[1:]:
        baseline_result = allocation.solve_allocation(
            baseline, fleet_size, refine=False
        )
        disruption_result = allocation.solve_allocation(
            disruption, fleet_size, refine=False
        )
        failure_result, failed_name = worst_failure_result(baseline, fleet_size)
        for state, result, failure_name in [
            ("Baseline roads", baseline_result, None),
            ("Matched restrictions closed", disruption_result, None),
            ("Worst single-point failure", failure_result, failed_name),
        ]:
            records.append(
                {
                    "Fleet Size": fleet_size,
                    "State": state,
                    "Delivered Water (L/day)": result.delivery_liters,
                    "Protected Share": result.delivery_liters / total_demand,
                    "Unmet Water (L/day)": total_demand - result.delivery_liters,
                    "Worst Failed Point": failure_name,
                }
            )
        print(f"Resource-curve optimization complete: fleet={fleet_size}")
    curve = pd.DataFrame(records)
    curve["Marginal Gain (pp/vehicle)"] = np.nan
    for state, index in curve.groupby("State", sort=False).groups.items():
        ordered = curve.loc[index].sort_values("Fleet Size")
        gain = (
            ordered["Protected Share"].diff()
            / ordered["Fleet Size"].diff()
            * 100.0
        )
        curve.loc[ordered.index, "Marginal Gain (pp/vehicle)"] = gain.to_numpy()
        if np.any(np.diff(ordered["Protected Share"].to_numpy()) < -1e-9):
            raise ValueError(f"Protected share is not monotonic for {state}")
    return curve.sort_values(["State", "Fleet Size"]).reset_index(drop=True)


def add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.10, 1.04, label, transform=ax.transAxes, fontsize=12,
        fontweight="bold", va="top", ha="left"
    )


def main() -> None:
    curve = calculate_resource_curve()
    sns.set_theme(style="whitegrid", context="paper")
    fig, axes = plt.subplots(1, 3, figsize=(14.8, 4.9))
    fig.subplots_adjust(left=0.065, right=0.99, top=0.96, bottom=0.23, wspace=0.25)

    for state in STATE_ORDER:
        selected = curve.loc[curve["State"].eq(state)].sort_values("Fleet Size")
        style = {
            "color": COLORS[state],
            "marker": MARKERS[state],
            "linewidth": 2.0,
            "markersize": 5.5,
            "label": state,
        }
        axes[0].plot(selected["Fleet Size"], selected["Protected Share"], **style)
        axes[1].plot(
            selected["Fleet Size"],
            selected["Unmet Water (L/day)"] / 1000.0,
            **style,
        )
        marginal = selected.dropna(subset=["Marginal Gain (pp/vehicle)"])
        axes[2].plot(
            marginal["Fleet Size"], marginal["Marginal Gain (pp/vehicle)"], **style
        )

    axes[0].set_ylabel("Fully protected affected residents")
    axes[0].yaxis.set_major_formatter(PercentFormatter(1.0))
    axes[0].set_ylim(bottom=0)
    axes[1].set_ylabel("Unmet minimum water (m3/day)")
    unmet_min = float(curve["Unmet Water (L/day)"].min() / 1000.0)
    unmet_max = float(curve["Unmet Water (L/day)"].max() / 1000.0)
    axes[1].set_ylim(unmet_min - 0.08 * (unmet_max - unmet_min), unmet_max * 1.005)
    axes[2].set_ylabel("Marginal protection gain (percentage points/vehicle)")
    axes[2].set_ylim(bottom=0)
    for label, ax in zip("abc", axes, strict=True):
        ax.set_xlabel("Available tankers")
        ax.set_xticks(FLEET_SIZES)
        ax.set_xlim(-0.4, 20.4)
        ax.grid(True, color="#d7dde2", linewidth=0.65)
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color("#374151")
            spine.set_linewidth(0.8)
        add_panel_label(ax, label)

    axes[0].text(
        0.03,
        0.97,
        "Central outage population\n3 L/person/day; 500 m access\nFull-mesh service required",
        transform=axes[0].transAxes,
        ha="left",
        va="top",
        fontsize=8.0,
        linespacing=1.2,
        bbox={
            "boxstyle": "round,pad=0.35", "facecolor": "white",
            "edgecolor": "#808080", "linewidth": 0.5, "alpha": 0.94,
        },
    )
    axes[2].text(
        0.97,
        0.05,
        "Gain averaged over each\npreceding fleet interval",
        transform=axes[2].transAxes,
        ha="right",
        va="bottom",
        fontsize=8.0,
        linespacing=1.2,
        bbox={
            "boxstyle": "round,pad=0.35", "facecolor": "white",
            "edgecolor": "#808080", "linewidth": 0.5, "alpha": 0.94,
        },
    )
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.02),
        ncol=3,
        frameon=True,
        framealpha=0.96,
        edgecolor="#808080",
        fontsize=8.0,
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    for state in STATE_ORDER:
        selected = curve.loc[curve["State"].eq(state)].sort_values("Fleet Size")
        shares = ", ".join(
            f"{int(row['Fleet Size'])}={row['Protected Share']:.3%}"
            for _, row in selected.iterrows()
        )
        print(f"{state} protected share: {shares}")
        failure_names = selected["Worst Failed Point"].dropna().tolist()
        if failure_names:
            print(f"Worst failed points by positive fleet level: {failure_names}")
    print(f"Saved: {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
