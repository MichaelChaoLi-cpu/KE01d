#!/usr/bin/env python3
"""Accessibility Coverage by Distance Threshold.

Plan: Compare cumulative nominal access coverage for affected residents, older
residents in outage-reporting municipalities, and shelter evacuees at the
approved 250, 500, and 1,000 m thresholds.
Framework: AnaSOP Sections 5-7 baseline shortest-road-distance and weighted
coverage equations using all 36 resolved announced water points and all 41
resolved current shelters. Road distance is a proxy, not observed walking.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.ticker import PercentFormatter

from figure_announced_water_points_and_nominal_access_coverage import (
    build_baseline_graph,
    nearest_water_point_node_distances,
)
from _figure_style import (
    BORDER_GREY,
    DISTANCE_COLORS,
    MID_GREY,
    PURPLE,
    VERMILLION,
    BLUE,
    annotation_box,
    panel_label,
    set_theme,
    style_cartesian_axis,
)


ROOT = Path(__file__).resolve().parents[2]
MESH_SCENARIOS = (
    ROOT / "data/processed/population_mesh_outage_demand_scenarios_preprocessed.parquet"
)
MESH_ACCESS = (
    ROOT / "data/processed/kumamoto_population_mesh_network_access_preprocessed.parquet"
)
DISCLOSURE_GROUPS = (
    ROOT / "data/processed/kumamoto_population_disclosure_groups_preprocessed.parquet"
)
GROUP_ACCESS = (
    ROOT / "data/processed/kumamoto_population_group_network_access_preprocessed.parquet"
)
SHELTERS = (
    ROOT / "data/processed/shelter_water_demand_network_access_preprocessed.parquet"
)
WATER_POINTS = (
    ROOT / "data/processed/emergency_water_points_network_access_preprocessed.parquet"
)
ROAD_NODES = ROOT / "data/processed/kumamoto_routable_road_nodes_preprocessed.parquet"
ROAD_EDGES = ROOT / "data/processed/kumamoto_routable_road_edges_preprocessed.parquet"
PARAMETERS = ROOT / "data/processed/emergency_water_scenario_parameters_preprocessed.parquet"
OUTPUT_PATH = (
    ROOT / "data/results/figures/Figure_accessibility_coverage_by_distance_threshold.png"
)

DISTANCE_COLUMN = "Nearest Water Point Network Distance (m)"
RESIDENT_COLOR = BLUE
OLDER_COLOR = VERMILLION
SHELTER_COLOR = PURPLE
DISPLAY_THRESHOLDS_M = np.array([250, 500, 1_000, 2_000, 5_000], dtype=float)
THRESHOLD_COLORS = [
    DISTANCE_COLORS["<=250 m"],
    DISTANCE_COLORS["250-500 m"],
    DISTANCE_COLORS["500-1,000 m"],
    DISTANCE_COLORS["1,000-2,000 m"],
    DISTANCE_COLORS["2,000-5,000 m"],
]


def attach_unit_distances(
    units: pd.DataFrame,
    eligible_edges: pd.DataFrame,
    node_distances: np.ndarray,
) -> pd.DataFrame:
    """Attach connector-aware nearest-water-point distance to analysis units."""
    result = units.copy()
    edge_lookup = eligible_edges[
        ["Road Edge ID", "From Index", "To Index", "Road Length (m)"]
    ].drop_duplicates("Road Edge ID")
    result = result.merge(
        edge_lookup,
        left_on="Access Road Edge ID",
        right_on="Road Edge ID",
        how="left",
        validate="many_to_one",
    )
    fraction = pd.to_numeric(result["Access Edge Fraction"], errors="coerce").clip(0, 1)
    edge_length = pd.to_numeric(result["Road Length (m)"], errors="coerce")
    from_index = result["From Index"].fillna(-1).astype(int).to_numpy()
    to_index = result["To Index"].fillna(-1).astype(int).to_numpy()
    valid = (from_index >= 0) & (to_index >= 0)
    along = np.full(len(result), np.inf, dtype=np.float64)
    along[valid] = np.minimum(
        node_distances[from_index[valid]]
        + fraction.to_numpy(np.float64)[valid]
        * edge_length.to_numpy(np.float64)[valid],
        node_distances[to_index[valid]]
        + (1.0 - fraction.to_numpy(np.float64)[valid])
        * edge_length.to_numpy(np.float64)[valid],
    )
    snap = pd.to_numeric(result["Network Snap Distance (m)"], errors="coerce").to_numpy(
        np.float64
    )
    accepted = result["Network Snap Accepted"].fillna(False).to_numpy(bool)
    result[DISTANCE_COLUMN] = np.where(
        accepted & np.isfinite(along) & np.isfinite(snap), along + snap, np.nan
    )
    return result


def weighted_curve(
    distances: pd.Series,
    weights: pd.Series,
    thresholds: np.ndarray,
    denominator_mask: pd.Series | None = None,
) -> tuple[np.ndarray, float, float]:
    """Return weighted cumulative coverage and denominator diagnostics."""
    distance = pd.to_numeric(distances, errors="coerce").to_numpy(np.float64)
    weight = pd.to_numeric(weights, errors="coerce").fillna(0).to_numpy(np.float64)
    eligible = weight > 0
    if denominator_mask is not None:
        eligible &= denominator_mask.fillna(False).to_numpy(bool)
    denominator = float(weight[eligible].sum())
    if denominator <= 0:
        raise ValueError("Coverage denominator is empty")
    finite_weight = float(weight[eligible & np.isfinite(distance)].sum())
    curve = np.asarray(
        [
            weight[eligible & np.isfinite(distance) & (distance <= threshold)].sum()
            / denominator
            for threshold in thresholds
        ],
        dtype=np.float64,
    )
    if np.any(np.diff(curve) < -1e-12):
        raise ValueError("Cumulative coverage is not monotonic")
    return curve, denominator, finite_weight / denominator


def approved_thresholds() -> np.ndarray:
    """Read and validate the approved access-distance parameter values."""
    parameters = pd.read_parquet(PARAMETERS)
    selected = parameters.loc[
        parameters["Parameter Name"].isin(
            ["General Access Distance", "Older Resident Access Distance"]
        )
    ].copy()
    values = pd.to_numeric(selected["Parameter Value"], errors="coerce").dropna()
    thresholds = np.sort(values.unique().astype(np.float64))
    expected = np.asarray([250.0, 500.0, 1000.0])
    if not np.array_equal(thresholds, expected):
        raise ValueError(f"Unexpected approved access thresholds: {thresholds.tolist()}")
    return thresholds


def add_panel_label(ax: plt.Axes, label: str) -> None:
    panel_label(ax, label, x=-0.08, y=1.04)


def add_summary(ax: plt.Axes, text: str) -> None:
    annotation_box(
        ax, text, x=0.03, y=0.97, va="top", fontsize=7.8
    )


def main() -> None:
    formal_thresholds = approved_thresholds()
    if not np.isin(formal_thresholds, DISPLAY_THRESHOLDS_M).all():
        raise ValueError("Formal thresholds are not contained in display thresholds")
    curve_thresholds = np.arange(0.0, DISPLAY_THRESHOLDS_M.max() + 5.0, 5.0)

    water = pd.read_parquet(WATER_POINTS)
    eligible_water = water.loc[
        water["Network Snap Accepted"].fillna(False)
        & water["Water Point Node ID"].notna()
    ].copy()
    if len(eligible_water) != 36 or water["Location Resolution Status"].eq("unmatched").any():
        raise ValueError("Expected all 36 announced water points to be network eligible")

    nodes = pd.read_parquet(ROAD_NODES, columns=["Network Node ID"])
    edges = pd.read_parquet(
        ROAD_EDGES,
        columns=[
            "Road Edge ID",
            "From Node ID",
            "To Node ID",
            "Road Length (m)",
            "Road Available",
            "Network Analysis Eligible",
        ],
    )
    graph, node_index, eligible_edges = build_baseline_graph(nodes, edges)
    node_distances = nearest_water_point_node_distances(
        graph, node_index, eligible_water
    )

    mesh_scenarios = pd.read_parquet(
        MESH_SCENARIOS,
        columns=[
            "Mesh Code",
            "Reporting Municipality Name",
            "Outage Population Scenario",
            "Demand Scenario",
            "Outage Household Ratio",
            "Estimated Outage Population",
        ],
    )
    mesh_scenarios = mesh_scenarios.loc[
        mesh_scenarios["Outage Population Scenario"].eq("proportional_central")
        & mesh_scenarios["Demand Scenario"].eq("minimum")
    ].copy()
    mesh_access = pd.read_parquet(MESH_ACCESS).drop(columns=["Geometry"], errors="ignore")
    residents = mesh_scenarios.merge(
        mesh_access, on="Mesh Code", how="left", validate="one_to_one"
    )
    residents = residents.loc[residents["Estimated Outage Population"].gt(0)].copy()
    residents = attach_unit_distances(residents, eligible_edges, node_distances)

    groups = pd.read_parquet(
        DISCLOSURE_GROUPS,
        columns=["Disclosure Group Code", "Population Age 65+"],
    )
    group_access = pd.read_parquet(GROUP_ACCESS).drop(columns=["Geometry"], errors="ignore")
    older = groups.merge(
        group_access, on="Disclosure Group Code", how="inner", validate="one_to_one"
    )
    older = older.merge(
        mesh_scenarios[
            ["Mesh Code", "Reporting Municipality Name", "Outage Household Ratio"]
        ],
        left_on="Representative Mesh Code",
        right_on="Mesh Code",
        how="left",
        validate="many_to_one",
    )
    older = older.loc[
        older["Outage Household Ratio"].gt(0) & older["Population Age 65+"].gt(0)
    ].copy()
    older = attach_unit_distances(older, eligible_edges, node_distances)

    shelters = pd.read_parquet(SHELTERS)
    shelters = shelters.loc[shelters["Demand Scenario"].eq("minimum")].drop_duplicates(
        "Shelter Number"
    )
    if len(shelters) != 41 or not shelters["Network Snap Accepted"].fillna(False).all():
        raise ValueError("Expected all 41 current shelters to be network eligible")
    shelters = attach_unit_distances(shelters, eligible_edges, node_distances)

    resident_curve, resident_denominator, resident_connected = weighted_curve(
        residents[DISTANCE_COLUMN],
        residents["Estimated Outage Population"],
        curve_thresholds,
    )
    older_curve, older_denominator, older_connected = weighted_curve(
        older[DISTANCE_COLUMN], older["Population Age 65+"], curve_thresholds
    )
    shelter_curve, shelter_denominator, shelter_connected = weighted_curve(
        shelters[DISTANCE_COLUMN], shelters["Evacuee People"], curve_thresholds
    )

    def values_at(curve: np.ndarray) -> np.ndarray:
        return curve[np.searchsorted(curve_thresholds, DISPLAY_THRESHOLDS_M)]

    resident_display = values_at(resident_curve)
    older_display = values_at(older_curve)
    shelter_display = values_at(shelter_curve)

    set_theme()
    fig, axes = plt.subplots(
        1, 3, figsize=(14.8, 4.9), sharex=True, sharey=True,
        constrained_layout=True,
    )

    axes[0].plot(
        curve_thresholds, resident_curve, color=RESIDENT_COLOR, linewidth=2.4
    )
    axes[0].scatter(
        DISPLAY_THRESHOLDS_M, resident_display, color=THRESHOLD_COLORS,
        edgecolor=BORDER_GREY,
        linewidth=0.6, s=35, zorder=4
    )
    add_summary(
        axes[0],
        "Affected residents\n"
        f"Population: {resident_denominator:,.0f}\n"
        f"Network distance defined: {resident_connected:.1%}",
    )

    axes[1].plot(curve_thresholds, older_curve, color=OLDER_COLOR, linewidth=2.4)
    axes[1].scatter(
        DISPLAY_THRESHOLDS_M, older_display, color=THRESHOLD_COLORS,
        edgecolor=BORDER_GREY,
        linewidth=0.6, s=35, zorder=4
    )
    add_summary(
        axes[1],
        "Residents age 65+\n"
        f"Population: {older_denominator:,.0f}\n"
        f"Network distance defined: {older_connected:.1%}",
    )

    axes[2].plot(
        curve_thresholds,
        shelter_curve,
        color=SHELTER_COLOR,
        linewidth=2.4,
    )
    axes[2].scatter(
        DISPLAY_THRESHOLDS_M, shelter_display, color=THRESHOLD_COLORS,
        edgecolor=BORDER_GREY,
        linewidth=0.6, s=35, zorder=4
    )
    add_summary(
        axes[2],
        "Shelter evacuees\n"
        f"Evacuees: {shelter_denominator:,.0f}\n"
        f"Network distance defined: {shelter_connected:.1%}",
    )

    for panel_index, (label, ax) in enumerate(zip("abc", axes, strict=True)):
        guide_linewidth = 1.25 if panel_index < 2 else 0.65
        guide_alpha = 0.88 if panel_index < 2 else 0.28
        for threshold, threshold_color in zip(
            DISPLAY_THRESHOLDS_M, THRESHOLD_COLORS, strict=True
        ):
            ax.axvline(
                threshold,
                color=threshold_color,
                linewidth=guide_linewidth,
                linestyle=(0, (3.0, 2.5)),
                alpha=guide_alpha,
                zorder=1,
            )
        ax.set_xlim(0, 5100)
        ax.set_ylim(0, 1.02)
        ax.set_xticks([0, *DISPLAY_THRESHOLDS_M])
        ax.set_xticklabels(["0", "250", "500", "1,000", "2,000", "5,000"])
        ax.tick_params(axis="x", labelrotation=30)
        for tick_label in ax.get_xticklabels():
            tick_label.set_ha("right")
        ax.yaxis.set_major_formatter(PercentFormatter(1.0))
        ax.set_xlabel("Maximum road-network distance (m)")
        style_cartesian_axis(ax)
        ax.set_axisbelow(True)
        add_panel_label(ax, label)
    axes[0].set_ylabel("Weighted population covered")

    if not np.isclose(shelter_connected, 1.0, atol=1e-12):
        raise ValueError("A shelter is disconnected from the baseline road graph")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print(f"Formal thresholds (m): {formal_thresholds.astype(int).tolist()}")
    print(
        f"Displayed thresholds (m): {DISPLAY_THRESHOLDS_M.astype(int).tolist()} "
        "(2,000 and 5,000 m are extended diagnostics)"
    )
    print(
        "Affected-resident coverage: "
        + ", ".join(
            f"{int(threshold)} m={coverage:.6%}"
            for threshold, coverage in zip(
                DISPLAY_THRESHOLDS_M, resident_display, strict=True
            )
        )
    )
    print(
        "Older-resident coverage: "
        + ", ".join(
            f"{int(threshold)} m={coverage:.6%}"
            for threshold, coverage in zip(
                DISPLAY_THRESHOLDS_M, older_display, strict=True
            )
        )
    )
    print(
        "Shelter-evacuee coverage: "
        + ", ".join(
            f"{int(threshold)} m={coverage:.6%}"
            for threshold, coverage in zip(
                DISPLAY_THRESHOLDS_M, shelter_display, strict=True
            )
        )
    )
    print("Shelter locations resolved: 41/41; unknown-location evacuees: 0")
    print(f"Saved: {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
