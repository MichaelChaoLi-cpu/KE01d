#!/usr/bin/env python3
"""Announced Water-Point Coverage under Alternative Access Distances.

Plan: Map positive-demand 125 m resident meshes covered by the 36 existing
announced water points at 250, 500, 1,000, 2,000, and 5,000 m baseline
road-network distance thresholds.
Framework: AnaSOP Sections 5-7 shortest road-network distance and weighted
resident-coverage equations. The 2,000 and 5,000 m panels are extended
researcher-defined diagnostics, not observed collection behavior.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from figure_accessibility_coverage_by_distance_threshold import (
    DISTANCE_COLUMN,
    attach_unit_distances,
)
from figure_announced_water_points_and_nominal_access_coverage import (
    build_baseline_graph,
    nearest_water_point_node_distances,
)
from figure_outage_population_and_emergency_water_demand import style_map


ROOT = Path(__file__).resolve().parents[2]
MESH_SCENARIOS = ROOT / (
    "data/processed/population_mesh_outage_demand_scenarios_preprocessed.parquet"
)
MESH_ACCESS = ROOT / (
    "data/processed/kumamoto_population_mesh_network_access_preprocessed.parquet"
)
WATER_POINTS = ROOT / "data/processed/emergency_water_points_network_access_preprocessed.parquet"
ROAD_NODES = ROOT / "data/processed/kumamoto_routable_road_nodes_preprocessed.parquet"
ROAD_EDGES = ROOT / "data/processed/kumamoto_routable_road_edges_preprocessed.parquet"
MUNICIPALITIES = ROOT / "data/processed/kumamoto_reporting_municipalities_preprocessed.parquet"
OUTPUT_PATH = ROOT / (
    "data/results/figures/"
    "Figure_announced_water_point_coverage_under_alternative_access_distances.png"
)

PROJECTED_CRS = 6670
THRESHOLDS_M = [250, 500, 1_000, 2_000, 5_000]
COVERED_COLOR = "#2a9d8f"
UNCOVERED_COLOR = "#e9c4c4"
UNDEFINED_COLOR = "#8d99ae"
POINT_COLOR = "#005f73"


def load_and_calculate() -> tuple[
    gpd.GeoDataFrame,
    gpd.GeoDataFrame,
    gpd.GeoDataFrame,
    pd.DataFrame,
]:
    water = gpd.read_parquet(WATER_POINTS)
    water = water.loc[
        water["Network Snap Accepted"].fillna(False)
        & water["Water Point Node ID"].notna()
        & water["Location Resolution Status"].ne("unmatched")
    ].copy()
    if len(water) != 36:
        raise ValueError(f"Expected 36 existing announced water points, found {len(water)}")

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
    node_distances = nearest_water_point_node_distances(graph, node_index, water)

    meshes = gpd.read_parquet(
        MESH_SCENARIOS,
        columns=[
            "Mesh Code",
            "Reporting Municipality Name",
            "Geometry",
            "Outage Population Scenario",
            "Demand Scenario",
            "Estimated Outage Population",
        ],
    )
    meshes = meshes.loc[
        meshes["Outage Population Scenario"].eq("proportional_central")
        & meshes["Demand Scenario"].eq("minimum")
        & meshes["Estimated Outage Population"].gt(0)
    ].copy()
    access = pd.read_parquet(MESH_ACCESS).drop(columns=["Geometry"], errors="ignore")
    meshes = meshes.merge(access, on="Mesh Code", how="left", validate="one_to_one")
    meshes = attach_unit_distances(meshes, eligible_edges, node_distances)
    meshes = gpd.GeoDataFrame(meshes, geometry="Geometry", crs=6668)

    denominator = float(meshes["Estimated Outage Population"].sum())
    records = []
    for threshold_m in THRESHOLDS_M:
        covered = meshes[DISTANCE_COLUMN].le(threshold_m)
        covered_population = float(
            meshes.loc[covered, "Estimated Outage Population"].sum()
        )
        records.append(
            {
                "Distance Threshold (m)": threshold_m,
                "Covered Meshes": int(covered.sum()),
                "Covered Population": covered_population,
                "Coverage Rate": covered_population / denominator,
            }
        )
    summary = pd.DataFrame(records)
    if np.any(np.diff(summary["Coverage Rate"].to_numpy(float)) < -1e-12):
        raise ValueError("Coverage is not monotonic across distance thresholds")
    undefined_population = float(
        meshes.loc[meshes[DISTANCE_COLUMN].isna(), "Estimated Outage Population"].sum()
    )
    if undefined_population > denominator * 0.01:
        raise ValueError("Undefined network distance exceeds 1% of the denominator")

    municipalities = gpd.read_parquet(MUNICIPALITIES)
    return meshes, water, municipalities, summary


def add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.035,
        1.025,
        label,
        transform=ax.transAxes,
        fontsize=12,
        fontweight="bold",
        va="top",
        ha="left",
    )


def draw_threshold_map(
    ax: plt.Axes,
    meshes: gpd.GeoDataFrame,
    water: gpd.GeoDataFrame,
    municipalities: gpd.GeoDataFrame,
    threshold_m: int,
    summary_row: pd.Series,
    projected_bounds: tuple[float, float, float, float],
    geographic_bounds: tuple[float, float, float, float],
) -> None:
    covered = meshes[DISTANCE_COLUMN].le(threshold_m)
    undefined = meshes[DISTANCE_COLUMN].isna()
    uncovered = ~covered & ~undefined

    meshes.loc[uncovered].plot(
        ax=ax,
        color=UNCOVERED_COLOR,
        edgecolor="none",
        rasterized=True,
        zorder=1,
    )
    meshes.loc[covered].plot(
        ax=ax,
        color=COVERED_COLOR,
        edgecolor="none",
        rasterized=True,
        zorder=2,
    )
    meshes.loc[undefined].plot(
        ax=ax,
        color=UNDEFINED_COLOR,
        edgecolor="none",
        rasterized=True,
        zorder=2,
    )
    municipalities.boundary.plot(
        ax=ax, color="#4b5563", linewidth=0.35, zorder=3
    )
    water.plot(
        ax=ax,
        marker="o",
        color=POINT_COLOR,
        edgecolor="white",
        linewidth=0.45,
        markersize=19,
        zorder=5,
    )
    style_map(ax, projected_bounds, geographic_bounds)
    ax.text(
        0.02,
        0.98,
        (
            f"{threshold_m:,} m road distance\n"
            f"Covered: {summary_row['Covered Population']:,.0f} residents "
            f"({summary_row['Coverage Rate']:.1%})\n"
            f"Covered meshes: {int(summary_row['Covered Meshes']):,}"
        ),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.5,
        linespacing=1.2,
        bbox={
            "boxstyle": "round,pad=0.35",
            "facecolor": "white",
            "edgecolor": "#808080",
            "linewidth": 0.5,
            "alpha": 0.94,
        },
        zorder=8,
    )


def draw_legend_panel(
    ax: plt.Axes,
) -> None:
    ax.axis("off")
    handles = [
        Patch(facecolor=COVERED_COLOR, edgecolor="none", label="Covered demand mesh"),
        Patch(facecolor=UNCOVERED_COLOR, edgecolor="none", label="Uncovered demand mesh"),
        Patch(facecolor=UNDEFINED_COLOR, edgecolor="none", label="Undefined network distance"),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=POINT_COLOR,
            markeredgecolor="white",
            markersize=7,
            label="Existing announced water point",
        ),
    ]
    ax.legend(
        handles=handles,
        loc="center",
        fontsize=9.0,
        frameon=True,
        framealpha=0.96,
        edgecolor="#808080",
    )


def main() -> None:
    meshes, water, municipalities, summary = load_and_calculate()
    affected = municipalities.loc[
        municipalities["Reporting Municipality Name"].isin(["八代市", "宇城市", "氷川町"])
    ].copy()
    if len(affected) != 3:
        raise ValueError("Expected three positive-outage municipalities")
    geographic_bounds = tuple(float(value) for value in affected.total_bounds)
    meshes = meshes.loc[meshes["Reporting Municipality Name"].notna()].to_crs(PROJECTED_CRS)
    water = water.to_crs(PROJECTED_CRS)
    municipalities = municipalities.to_crs(PROJECTED_CRS)
    affected = affected.to_crs(PROJECTED_CRS)
    projected_bounds = tuple(float(value) for value in affected.total_bounds)

    sns.set_theme(style="white", context="paper")
    fig, axes = plt.subplots(2, 3, figsize=(15.8, 7.7))
    fig.subplots_adjust(
        left=0.045, right=0.985, top=0.975, bottom=0.04, wspace=0.15, hspace=0.12
    )
    map_axes = list(axes.flat[:5])
    for label, ax, threshold_m in zip("abcde", map_axes, THRESHOLDS_M, strict=True):
        summary_row = summary.loc[
            summary["Distance Threshold (m)"].eq(threshold_m)
        ].iloc[0]
        draw_threshold_map(
            ax,
            meshes,
            water,
            municipalities,
            threshold_m,
            summary_row,
            projected_bounds,
            geographic_bounds,
        )
        add_panel_label(ax, label)
    draw_legend_panel(axes.flat[5])
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    for row in summary.itertuples(index=False):
        print(
            f"{int(row[0]):,} m: covered={row[2]:,.0f}; "
            f"coverage={row[3]:.2%}; meshes={int(row[1]):,}"
        )
    print(f"Saved: {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
