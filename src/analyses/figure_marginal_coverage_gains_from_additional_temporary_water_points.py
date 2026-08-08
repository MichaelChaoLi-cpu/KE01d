#!/usr/bin/env python3
"""Marginal Coverage Gains from Additional Temporary Water Points.

Plan: Map the nested greedy sequence of screened temporary sites, trace
access-only affected-population coverage as sites are added, and compare
capacity-constrained protected shares under 5-, 10-, and 20-tanker fleets.
Framework: AnaSOP Sections 5-7 central outage population, minimum resident
demand, 500 m road-network access, the temporary-site budget constraint, the
nested marginal-access heuristic, and the route-constrained resident ledger.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter

import figure_scenario_based_tanker_and_temporary_water_point_allocation as allocation
from figure_outage_population_and_emergency_water_demand import style_map


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT / (
    "data/results/figures/"
    "Figure_marginal_coverage_gains_from_additional_temporary_water_points.png"
)
PROJECTED_CRS = 6670
SITE_BUDGETS = [0, 1, 3, 5, 10, 20, 35]
FLEET_SIZES = [5, 10, 20]
ACCESS_STATES = [
    "Baseline roads",
    "Matched restrictions closed",
    "Worst single announced-point failure",
]
STATE_COLORS = {
    "Baseline roads": "#087e8b",
    "Matched restrictions closed": "#d97706",
    "Worst single announced-point failure": "#7b2cbf",
}
STATE_MARKERS = {
    "Baseline roads": "o",
    "Matched restrictions closed": "s",
    "Worst single announced-point failure": "^",
}
FLEET_COLORS = {5: "#4c78a8", 10: "#f58518", 20: "#54a24b"}


def load_scenarios() -> tuple[
    allocation.ScenarioInputs,
    allocation.ScenarioInputs,
    gpd.GeoDataFrame,
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
    restrictions = pd.read_parquet(
        allocation.RESTRICTIONS,
        columns=["Matched Road Edge ID", "Road Edge Match Status"],
    )
    closed_edges = set(
        restrictions.loc[
            restrictions["Road Edge Match Status"].eq("matched_primary"),
            "Matched Road Edge ID",
        ]
        .dropna()
        .astype(str)
    )
    older_weight = allocation.older_priority_weights()
    baseline = allocation.prepare_scenario(
        "Baseline roads",
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
    )
    disruption = allocation.prepare_scenario(
        "Matched restrictions closed",
        closed_edges,
        None,
        nodes,
        edges,
        demand,
        access,
        water,
        staging,
        parameters,
        older_weight,
    )
    if not np.isclose(allocation.ACCESS_DISTANCE_M, 500.0):
        raise ValueError("The central access threshold is no longer 500 m")
    if baseline.sites["Temporary Site"].sum() != 35:
        raise ValueError("Expected 35 screened, network-eligible temporary candidates")
    return baseline, disruption, demand


def covered_unit_indices(
    scenario: allocation.ScenarioInputs,
    temporary_ids: set[str],
    failed_existing_index: int | None = None,
    threshold_m: float | None = None,
) -> np.ndarray:
    existing = ~scenario.sites["Temporary Site"].to_numpy(bool)
    allowed = existing.copy()
    if temporary_ids:
        allowed |= (
            scenario.sites["Temporary Site"].to_numpy(bool)
            & scenario.sites["Site ID"].astype(str).isin(temporary_ids).to_numpy()
        )
    if failed_existing_index is not None:
        allowed[failed_existing_index] = False
    site_indices = np.flatnonzero(allowed)
    eligible_arcs = scenario.arcs.loc[
        scenario.arcs["Site Index"].isin(site_indices)
    ]
    if threshold_m is not None:
        eligible_arcs = eligible_arcs.loc[
            eligible_arcs["Distance (m)"].le(threshold_m)
        ]
    units = eligible_arcs["Unit Index"].unique()
    return np.sort(units.astype(np.int32))


def coverage_share(
    scenario: allocation.ScenarioInputs,
    temporary_ids: set[str],
    failed_existing_index: int | None = None,
    threshold_m: float | None = None,
) -> float:
    population = scenario.units["Estimated Outage Population"].to_numpy(float)
    covered = covered_unit_indices(
        scenario, temporary_ids, failed_existing_index, threshold_m
    )
    return float(population[covered].sum() / population.sum())


def greedy_site_sequence(
    baseline: allocation.ScenarioInputs,
) -> tuple[list[str], list[float]]:
    population = baseline.units["Estimated Outage Population"].to_numpy(float)
    existing_covered = set(covered_unit_indices(baseline, set()).tolist())
    temp_rows = baseline.sites.loc[baseline.sites["Temporary Site"]].copy()
    temp_rows["Site ID"] = temp_rows["Site ID"].astype(str)
    if temp_rows["Site ID"].duplicated().any():
        raise ValueError("Temporary candidate identifiers are not unique")
    units_by_site: dict[str, set[int]] = {}
    for site_index, site_id in zip(temp_rows.index, temp_rows["Site ID"], strict=True):
        units_by_site[site_id] = set(
            baseline.arcs.loc[
                baseline.arcs["Site Index"].eq(site_index), "Unit Index"
            ]
            .astype(int)
            .tolist()
        )

    selected: list[str] = []
    gains: list[float] = []
    covered = existing_covered.copy()
    remaining = sorted(units_by_site)
    while remaining:
        best_id: str | None = None
        best_gain = -1.0
        for site_id in remaining:
            new_units = np.fromiter(units_by_site[site_id] - covered, dtype=np.int32)
            gain = float(population[new_units].sum()) if len(new_units) else 0.0
            if gain > best_gain + 1e-9:
                best_id = site_id
                best_gain = gain
        if best_id is None:
            raise RuntimeError("Greedy candidate selection failed")
        selected.append(best_id)
        gains.append(best_gain)
        covered.update(units_by_site[best_id])
        remaining.remove(best_id)
    return selected, gains


def access_curve(
    baseline: allocation.ScenarioInputs,
    disruption: allocation.ScenarioInputs,
    sequence: list[str],
) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    existing_indices = np.flatnonzero(
        ~baseline.sites["Temporary Site"].to_numpy(bool)
    )
    for site_count in range(len(sequence) + 1):
        selected = set(sequence[:site_count])
        records.append(
            {
                "Additional Sites": site_count,
                "Road and Point State": "Baseline roads",
                "Access Coverage": coverage_share(baseline, selected),
                "Worst Failed Point": None,
            }
        )
        records.append(
            {
                "Additional Sites": site_count,
                "Road and Point State": "Matched restrictions closed",
                "Access Coverage": coverage_share(disruption, selected),
                "Worst Failed Point": None,
            }
        )
        failure_results = [
            (
                coverage_share(baseline, selected, int(site_index)),
                str(baseline.sites.iloc[int(site_index)]["Site Name"]),
            )
            for site_index in existing_indices
        ]
        worst_coverage, failed_name = min(failure_results, key=lambda item: item[0])
        records.append(
            {
                "Additional Sites": site_count,
                "Road and Point State": "Worst single announced-point failure",
                "Access Coverage": worst_coverage,
                "Worst Failed Point": failed_name,
            }
        )
    curve = pd.DataFrame(records)
    for state, group in curve.groupby("Road and Point State", sort=False):
        ordered = group.sort_values("Additional Sites")
        if np.any(np.diff(ordered["Access Coverage"].to_numpy(float)) < -1e-10):
            raise ValueError(f"Access coverage is not monotonic for {state}")
    return curve


def capacity_curve(
    baseline: allocation.ScenarioInputs,
) -> pd.DataFrame:
    total_demand = float(baseline.units["Estimated Water Demand (L/day)"].sum())
    records: list[dict[str, object]] = []
    for site_count in SITE_BUDGETS:
        for fleet_size in FLEET_SIZES:
            result = allocation.solve_allocation(
                baseline,
                fleet_size,
                refine=False,
                temporary_site_budget=site_count,
            )
            records.append(
                {
                    "Additional Sites": site_count,
                    "Fleet Size": fleet_size,
                    "Protected Share": result.delivery_liters / total_demand,
                    "Temporary Sites Used": int(
                        result.selected_sites["Temporary Site"].sum()
                    ),
                }
            )
            print(
                "Site-resource optimization complete: "
                f"sites={site_count}, fleet={fleet_size}"
            )
    curve = pd.DataFrame(records)
    for fleet_size, group in curve.groupby("Fleet Size", sort=False):
        ordered = group.sort_values("Additional Sites")
        if np.any(np.diff(ordered["Protected Share"].to_numpy(float)) < -1e-9):
            raise ValueError(f"Protected share is not monotonic for fleet {fleet_size}")
        if np.any(ordered["Temporary Sites Used"].to_numpy(int) > ordered["Additional Sites"]):
            raise ValueError(f"Temporary-site budget violated for fleet {fleet_size}")
    return curve


def add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.08,
        1.035,
        label,
        transform=ax.transAxes,
        fontsize=12,
        fontweight="bold",
        va="top",
        ha="left",
    )


def draw_map(
    ax: plt.Axes,
    baseline: allocation.ScenarioInputs,
    sequence: list[str],
    gains: list[float],
    access: pd.DataFrame,
) -> None:
    municipalities = gpd.read_parquet(allocation.MUNICIPALITIES)
    affected = municipalities.loc[
        municipalities["Reporting Municipality Name"].isin(["八代市", "宇城市", "氷川町"])
    ].copy()
    if len(affected) != 3:
        raise ValueError("Expected three positive-outage municipalities")
    geographic_bounds = tuple(float(value) for value in affected.total_bounds)
    municipalities = municipalities.to_crs(PROJECTED_CRS)
    affected = affected.to_crs(PROJECTED_CRS)
    projected_bounds = tuple(float(value) for value in affected.total_bounds)

    units = baseline.units.to_crs(PROJECTED_CRS)
    units.plot(
        ax=ax,
        column="Estimated Outage Population",
        cmap="Blues",
        alpha=0.58,
        edgecolor="none",
        rasterized=True,
        zorder=1,
    )
    municipalities.boundary.plot(ax=ax, color="#4b5563", linewidth=0.35, zorder=3)

    sites = baseline.sites.to_crs(PROJECTED_CRS).copy()
    temporary = sites.loc[sites["Temporary Site"]].copy()
    existing = sites.loc[~sites["Temporary Site"]].copy()
    temporary.plot(
        ax=ax,
        marker="*",
        facecolor="none",
        edgecolor="#8b8f94",
        linewidth=0.65,
        markersize=30,
        zorder=4,
    )
    existing.plot(
        ax=ax,
        marker="o",
        color="#087e8b",
        edgecolor="white",
        linewidth=0.4,
        markersize=18,
        zorder=5,
    )
    rank = {site_id: index for index, site_id in enumerate(sequence, start=1)}
    gain = {site_id: value for site_id, value in zip(sequence, gains, strict=True)}
    selected = temporary.loc[temporary["Site ID"].astype(str).isin(rank)].copy()
    selected["Selection Rank"] = selected["Site ID"].astype(str).map(rank)
    selected["Incremental Population"] = selected["Site ID"].astype(str).map(gain)
    positive = selected.loc[selected["Incremental Population"].gt(0)].copy()
    if not positive.empty:
        positive.plot(
            ax=ax,
            column="Selection Rank",
            cmap="plasma_r",
            marker="*",
            edgecolor="white",
            linewidth=0.5,
            markersize=74,
            zorder=6,
        )
        for _, row in positive.iterrows():
            ax.annotate(
                str(int(row["Selection Rank"])),
                xy=(row.Geometry.x, row.Geometry.y),
                xytext=(3, 3),
                textcoords="offset points",
                fontsize=6.5,
                color="#3b1d5a",
                fontweight="bold",
                zorder=7,
            )

    style_map(ax, projected_bounds, geographic_bounds)
    baseline_curve = access.loc[
        access["Road and Point State"].eq("Baseline roads")
    ].sort_values("Additional Sites")
    initial = float(baseline_curve.iloc[0]["Access Coverage"])
    final = float(baseline_curve.iloc[-1]["Access Coverage"])
    ax.text(
        0.02,
        0.98,
        (
            "Greedy nested sequence\n"
            f"35 screened candidates; {len(positive)} add coverage\n"
            f"500 m access: {initial:.1%} to {final:.1%}"
        ),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.8,
        linespacing=1.2,
        bbox={
            "boxstyle": "round,pad=0.35",
            "facecolor": "white",
            "edgecolor": "#808080",
            "linewidth": 0.5,
            "alpha": 0.94,
        },
        zorder=9,
    )
    ax.legend(
        handles=[
            Line2D(
                [0], [0], marker="o", color="none", markerfacecolor="#087e8b",
                markeredgecolor="white", markersize=6, label="Announced point"
            ),
            Line2D(
                [0], [0], marker="*", color="none", markerfacecolor="none",
                markeredgecolor="#8b8f94", markersize=8, label="Screened candidate"
            ),
            Line2D(
                [0], [0], marker="*", color="none", markerfacecolor="#d55e00",
                markeredgecolor="white", markersize=9, label="Positive-gain selection"
            ),
        ],
        loc="lower left",
        fontsize=6.8,
        frameon=True,
        framealpha=0.94,
        edgecolor="#808080",
    )


def draw_access_curve(ax: plt.Axes, curve: pd.DataFrame) -> None:
    for state in ACCESS_STATES:
        selected = curve.loc[curve["Road and Point State"].eq(state)].sort_values(
            "Additional Sites"
        )
        ax.plot(
            selected["Additional Sites"],
            selected["Access Coverage"],
            color=STATE_COLORS[state],
            marker=STATE_MARKERS[state],
            markevery=SITE_BUDGETS,
            linewidth=2.0,
            markersize=5.0,
            label=state,
        )
    ax.set_xlabel("Additional temporary water points")
    ax.set_ylabel("Affected residents within 500 m")
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.set_xlim(-0.5, 35.5)
    ax.set_xticks(SITE_BUDGETS)
    coverage_min = float(curve["Access Coverage"].min())
    coverage_max = float(curve["Access Coverage"].max())
    ax.set_ylim(
        bottom=max(0, coverage_min - 0.012),
        top=min(1.0, coverage_max + 0.012),
    )
    ax.text(
        0.03,
        0.97,
        "Access only\nSame baseline-selected site sequence",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.0,
        bbox={
            "boxstyle": "round,pad=0.35",
            "facecolor": "white",
            "edgecolor": "#808080",
            "linewidth": 0.5,
            "alpha": 0.94,
        },
    )
    ax.legend(loc="upper right", fontsize=7.0, frameon=True, edgecolor="#808080")


def draw_capacity_curve(ax: plt.Axes, curve: pd.DataFrame) -> None:
    for fleet_size in FLEET_SIZES:
        selected = curve.loc[curve["Fleet Size"].eq(fleet_size)].sort_values(
            "Additional Sites"
        )
        ax.plot(
            selected["Additional Sites"],
            selected["Protected Share"],
            color=FLEET_COLORS[fleet_size],
            marker="o",
            linewidth=2.0,
            markersize=5.0,
            label=f"{fleet_size} tankers",
        )
    ax.set_xlabel("Additional temporary water points")
    ax.set_ylabel("Fully protected affected residents")
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.set_xlim(-0.5, 35.5)
    ax.set_xticks(SITE_BUDGETS)
    ax.set_ylim(bottom=0, top=min(1.005, float(curve["Protected Share"].max()) + 0.07))
    ax.text(
        0.03,
        0.97,
        "Site-budget optimized\nBaseline roads; 3 L/person/day",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.0,
        bbox={
            "boxstyle": "round,pad=0.35",
            "facecolor": "white",
            "edgecolor": "#808080",
            "linewidth": 0.5,
            "alpha": 0.94,
        },
    )
    ax.legend(loc="lower right", fontsize=7.2, frameon=True, edgecolor="#808080")


def style_line_panel(ax: plt.Axes) -> None:
    ax.grid(True, color="#d7dde2", linewidth=0.65)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("#374151")
        spine.set_linewidth(0.8)


def main() -> None:
    baseline, disruption, _ = load_scenarios()
    sequence, gains = greedy_site_sequence(baseline)
    access = access_curve(baseline, disruption, sequence)
    capacity = capacity_curve(baseline)

    sns.set_theme(style="whitegrid", context="paper")
    fig = plt.figure(figsize=(16.5, 6.1))
    grid = fig.add_gridspec(
        1, 3, width_ratios=[1.30, 1.0, 1.0],
        left=0.055, right=0.99, top=0.955, bottom=0.18, wspace=0.25
    )
    axes = [fig.add_subplot(grid[0, index]) for index in range(3)]
    draw_map(axes[0], baseline, sequence, gains, access)
    draw_access_curve(axes[1], access)
    draw_capacity_curve(axes[2], capacity)
    style_line_panel(axes[1])
    style_line_panel(axes[2])
    for label, ax in zip("abc", axes, strict=True):
        add_panel_label(ax, label)

    fig.text(
        0.5,
        0.045,
        (
            "Temporary sites are researcher-defined candidates. Access coverage does not imply "
            "water availability; protected share additionally enforces route-based tanker capacity."
        ),
        ha="center",
        va="bottom",
        fontsize=7.5,
        color="#4b5563",
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    baseline_access = access.loc[
        access["Road and Point State"].eq("Baseline roads")
        & access["Additional Sites"].isin(SITE_BUDGETS)
    ].sort_values("Additional Sites")
    print("Baseline access curve:")
    for row in baseline_access.itertuples(index=False):
        print(f"  sites={row[0]:2d}: coverage={row[2]:.2%}")
    print(f"Positive-gain temporary sites: {sum(value > 0 for value in gains)}/35")
    print(f"Saved: {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
