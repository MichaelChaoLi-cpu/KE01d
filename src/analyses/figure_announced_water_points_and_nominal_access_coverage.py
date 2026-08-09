#!/usr/bin/env python3
"""Announced Water Points and Nominal Access Coverage.

Plan: Map all announced water points, distinguish the 19 locations recovered
from announcement-linked map evidence, and compare 500 m nominal network
coverage before and after location recovery. Unmatched population meshes are
omitted from display.
Framework: AnaSOP Sections 5-7 nominal network accessibility equations.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Patch
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from figure_outage_population_and_emergency_water_demand import style_map
from _figure_style import (
    ANNOTATION_GREY,
    BLACK,
    BOUNDARY_GREY,
    DISTANCE_COLORS,
    GREEN,
    LIGHT_GREY,
    PANEL_FILL,
    PURPLE,
    YELLOW,
    annotation_box,
    panel_label,
    set_theme,
)


ROOT = Path(__file__).resolve().parents[2]
MESH_SCENARIOS = (
    ROOT
    / "data/processed/population_mesh_outage_demand_scenarios_preprocessed.parquet"
)
MESH_ACCESS = (
    ROOT / "data/processed/kumamoto_population_mesh_network_access_preprocessed.parquet"
)
WATER_POINTS = (
    ROOT / "data/processed/emergency_water_points_network_access_preprocessed.parquet"
)
MUNICIPALITIES = (
    ROOT / "data/processed/kumamoto_reporting_municipalities_preprocessed.parquet"
)
ROAD_NODES = ROOT / "data/processed/kumamoto_routable_road_nodes_preprocessed.parquet"
ROAD_EDGES = ROOT / "data/processed/kumamoto_routable_road_edges_preprocessed.parquet"
OUTPUT_PATH = (
    ROOT
    / "data/results/figures/Figure_announced_water_points_and_nominal_access_coverage.png"
)

PROJECTED_CRS = 6670
ACCESS_THRESHOLD_M = 500.0
ORIGINAL_COLOR = BLACK
RECOVERED_COLOR = PURPLE
COVERED_COLOR = GREEN
GAINED_COLOR = YELLOW
UNCOVERED_COLOR = "#E7C4D7"
UNDEFINED_COLOR = LIGHT_GREY
AFFECTED_COLOR = "#F3C892"
DISTANCE_LABELS = [
    "<=250 m",
    "250-500 m",
    "500-1,000 m",
    "1,000-2,000 m",
    "2,000-5,000 m",
    ">5,000 m or unreachable",
]


def plot_distance_bands(
    ax: plt.Axes,
    meshes: gpd.GeoDataFrame,
    distance_column: str,
) -> None:
    """Plot affected meshes in mutually exclusive nearest-point distance bands."""
    distance = pd.to_numeric(meshes[distance_column], errors="coerce")
    masks = {
        "<=250 m": distance.le(250),
        "250-500 m": distance.gt(250) & distance.le(500),
        "500-1,000 m": distance.gt(500) & distance.le(1_000),
        "1,000-2,000 m": distance.gt(1_000) & distance.le(2_000),
        "2,000-5,000 m": distance.gt(2_000) & distance.le(5_000),
        ">5,000 m or unreachable": distance.gt(5_000) | distance.isna(),
    }
    assigned = pd.Series(False, index=meshes.index)
    for label in DISTANCE_LABELS:
        mask = masks[label]
        assigned |= mask
        meshes.loc[mask].plot(
            ax=ax,
            color=DISTANCE_COLORS[label],
            edgecolor="none",
            rasterized=True,
            zorder=2,
        )
    if not assigned.all():
        raise ValueError(f"Unassigned distance-band meshes for {distance_column}")


def build_baseline_graph(
    nodes: pd.DataFrame, edges: pd.DataFrame
) -> tuple[csr_matrix, pd.Series, pd.DataFrame]:
    """Build an undirected minimum-length sparse road graph."""
    node_index = pd.Series(
        np.arange(len(nodes), dtype=np.int32),
        index=nodes["Network Node ID"].astype(str),
    )
    retained = edges.loc[
        edges["Road Available"].fillna(False)
        & edges["Network Analysis Eligible"].fillna(False)
    ].copy()
    retained["From Index"] = retained["From Node ID"].astype(str).map(node_index)
    retained["To Index"] = retained["To Node ID"].astype(str).map(node_index)
    retained = retained.dropna(subset=["From Index", "To Index", "Road Length (m)"])
    retained["From Index"] = retained["From Index"].astype(np.int32)
    retained["To Index"] = retained["To Index"].astype(np.int32)
    retained["Pair A"] = np.minimum(retained["From Index"], retained["To Index"])
    retained["Pair B"] = np.maximum(retained["From Index"], retained["To Index"])
    pairs = retained.groupby(["Pair A", "Pair B"], observed=True, sort=False)[
        "Road Length (m)"
    ].min().reset_index()
    rows = np.concatenate(
        [pairs["Pair A"].to_numpy(np.int32), pairs["Pair B"].to_numpy(np.int32)]
    )
    columns = np.concatenate(
        [pairs["Pair B"].to_numpy(np.int32), pairs["Pair A"].to_numpy(np.int32)]
    )
    weights = np.tile(pairs["Road Length (m)"].to_numpy(np.float64), 2)
    graph = csr_matrix((weights, (rows, columns)), shape=(len(nodes), len(nodes)))
    return graph, node_index, retained


def nearest_water_point_node_distances(
    graph: csr_matrix,
    node_index: pd.Series,
    resolved_points: pd.DataFrame,
) -> np.ndarray:
    """Return distance from each road node to the nearest resolved water point."""
    sources = resolved_points[["Water Point Node ID", "Network Snap Distance (m)"]].copy()
    sources["Node Index"] = sources["Water Point Node ID"].astype(str).map(node_index)
    sources = sources.dropna(subset=["Node Index"])
    sources["Node Index"] = sources["Node Index"].astype(np.int32)
    sources = sources.sort_values("Network Snap Distance (m)").drop_duplicates(
        "Node Index", keep="first"
    )
    if sources.empty:
        raise ValueError("No resolved announced water point maps to the baseline graph")
    distances = dijkstra(
        graph,
        directed=True,
        indices=sources["Node Index"].to_numpy(np.int32),
        return_predecessors=False,
    )
    if distances.ndim == 1:
        distances = distances[np.newaxis, :]
    offsets = sources["Network Snap Distance (m)"].to_numpy(np.float64)[:, None]
    return np.min(distances + offsets, axis=0)


def attach_mesh_distances(
    meshes: gpd.GeoDataFrame,
    access: pd.DataFrame,
    eligible_edges: pd.DataFrame,
    node_index: pd.Series,
    node_distances: np.ndarray,
    output_column: str,
) -> gpd.GeoDataFrame:
    """Attach connector-aware network distance to every population mesh."""
    access = access.copy()
    access["Mesh Code"] = access["Mesh Code"].astype(str)
    edge_lookup = eligible_edges[
        ["Road Edge ID", "From Index", "To Index", "Road Length (m)"]
    ].drop_duplicates("Road Edge ID")
    access = access.merge(
        edge_lookup,
        left_on="Access Road Edge ID",
        right_on="Road Edge ID",
        how="left",
        validate="many_to_one",
    )
    fraction = pd.to_numeric(access["Access Edge Fraction"], errors="coerce").clip(0, 1)
    length = pd.to_numeric(access["Road Length (m)"], errors="coerce")
    from_index = access["From Index"].fillna(-1).astype(int).to_numpy()
    to_index = access["To Index"].fillna(-1).astype(int).to_numpy()
    valid_indices = (from_index >= 0) & (to_index >= 0)
    along = np.full(len(access), np.inf, dtype=np.float64)
    along[valid_indices] = np.minimum(
        node_distances[from_index[valid_indices]]
        + fraction.to_numpy(np.float64)[valid_indices]
        * length.to_numpy(np.float64)[valid_indices],
        node_distances[to_index[valid_indices]]
        + (1.0 - fraction.to_numpy(np.float64)[valid_indices])
        * length.to_numpy(np.float64)[valid_indices],
    )
    snap = pd.to_numeric(access["Network Snap Distance (m)"], errors="coerce").to_numpy(
        np.float64
    )
    accepted = access["Network Snap Accepted"].fillna(False).to_numpy(bool)
    access[output_column] = np.where(
        accepted & np.isfinite(along) & np.isfinite(snap), along + snap, np.nan
    )
    meshes = meshes.copy()
    meshes["Mesh Code"] = meshes["Mesh Code"].astype(str)
    return meshes.merge(
        access[["Mesh Code", output_column]],
        on="Mesh Code",
        how="left",
        validate="one_to_one",
    )


def load_and_estimate() -> tuple[
    gpd.GeoDataFrame,
    gpd.GeoDataFrame,
    gpd.GeoDataFrame,
    gpd.GeoDataFrame,
    gpd.GeoDataFrame,
    tuple[float, float, float, float],
]:
    """Load inputs and calculate pre- and post-recovery 500 m network access."""
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
    ].copy()
    municipalities = gpd.read_parquet(
        MUNICIPALITIES,
        columns=["Reporting Municipality Name", "Geometry"],
    )
    water = gpd.read_parquet(WATER_POINTS)
    complete = water.loc[
        water["Location Resolution Status"].ne("unmatched")
        & water["Network Snap Accepted"].fillna(False)
        & water["Water Point Node ID"].notna()
    ].copy()
    recovered = complete.loc[
        complete["Location Resolution Status"].eq(
            "matched_announcement_linked_map_coordinate"
        )
    ].copy()
    original = complete.loc[
        ~complete.index.isin(recovered.index)
    ].copy()

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
    original_node_distances = nearest_water_point_node_distances(
        graph, node_index, original
    )
    complete_node_distances = nearest_water_point_node_distances(
        graph, node_index, complete
    )
    access = pd.read_parquet(
        MESH_ACCESS,
        columns=[
            "Mesh Code",
            "Network Snap Distance (m)",
            "Network Snap Accepted",
            "Access Road Edge ID",
            "Access Edge Fraction",
        ],
    )
    meshes = attach_mesh_distances(
        meshes,
        access,
        eligible_edges,
        node_index,
        original_node_distances,
        "Nearest Original Point Network Distance (m)",
    )
    meshes = attach_mesh_distances(
        meshes,
        access,
        eligible_edges,
        node_index,
        complete_node_distances,
        "Nearest Complete Point Network Distance (m)",
    )
    meshes["Affected"] = meshes["Estimated Outage Population"].gt(0)
    original_distance = meshes["Nearest Original Point Network Distance (m)"]
    complete_distance = meshes["Nearest Complete Point Network Distance (m)"]
    meshes["Original Covered"] = (
        meshes["Affected"] & original_distance.le(ACCESS_THRESHOLD_M)
    )
    meshes["Complete Covered"] = (
        meshes["Affected"] & complete_distance.le(ACCESS_THRESHOLD_M)
    )
    meshes["Coverage Gained"] = (
        meshes["Complete Covered"] & ~meshes["Original Covered"]
    )
    geographic_bounds = tuple(float(value) for value in municipalities.total_bounds)
    return (
        meshes.to_crs(PROJECTED_CRS),
        municipalities.to_crs(PROJECTED_CRS),
        original.to_crs(PROJECTED_CRS),
        recovered.to_crs(PROJECTED_CRS),
        water,
        geographic_bounds,
    )


def add_panel_label(ax: plt.Axes, label: str) -> None:
    panel_label(ax, label)


def add_summary(ax: plt.Axes, text: str) -> None:
    annotation_box(ax, text, fontsize=8.1)


def draw_legend_panel(ax: plt.Axes) -> None:
    """Draw one compact legend shared by all three map panels."""
    ax.set_axis_off()
    card = ax.inset_axes([0.17, 0.18, 0.66, 0.64])
    card.set_axis_off()
    card.add_patch(
        FancyBboxPatch(
            (0.02, 0.02),
            0.96,
            0.96,
            boxstyle="round,pad=0.006,rounding_size=0.02",
            transform=card.transAxes,
            facecolor=PANEL_FILL,
            edgecolor=ANNOTATION_GREY,
            linewidth=0.8,
        )
    )
    card.text(
        0.08, 0.92, "Legend", transform=card.transAxes,
        fontsize=9.0, fontweight="bold", va="top",
    )
    card.text(
        0.08, 0.81, "Location evidence", transform=card.transAxes,
        fontsize=7.1, va="top",
    )
    location_legend = card.legend(
        handles=[
            Patch(
                facecolor=AFFECTED_COLOR, edgecolor=ANNOTATION_GREY,
                label="Affected demand mesh (panel a)",
            ),
            Line2D(
                [0], [0], marker="o", color="none", markerfacecolor=ORIGINAL_COLOR,
                markeredgecolor="white", markersize=6,
                label="Previously resolved point",
            ),
            Line2D(
                [0], [0], marker="^", color="none", markerfacecolor=RECOVERED_COLOR,
                markeredgecolor="white", markersize=7,
                label="Recovered announcement-linked location",
            ),
        ],
        loc="upper left",
        bbox_to_anchor=(0.06, 0.77),
        frameon=False,
        fontsize=6.5,
        handlelength=1.4,
        handletextpad=0.55,
        labelspacing=0.3,
    )
    card.add_artist(location_legend)
    card.text(
        0.08, 0.49, "Nearest eligible point distance", transform=card.transAxes,
        fontsize=7.1, va="top",
    )
    card.legend(
        handles=[
            Patch(
                facecolor=DISTANCE_COLORS[label],
                edgecolor=ANNOTATION_GREY,
                label=label,
            )
            for label in DISTANCE_LABELS
        ],
        loc="upper left",
        bbox_to_anchor=(0.06, 0.455),
        frameon=False,
        fontsize=6.3,
        handlelength=1.4,
        handletextpad=0.55,
        labelspacing=0.22,
    )


def main() -> None:
    (
        meshes,
        municipalities,
        original,
        recovered,
        water,
        geographic_bounds,
    ) = load_and_estimate()
    study_municipalities = municipalities.loc[
        municipalities["Reporting Municipality Name"].isin(
            ["八代市", "宇城市", "氷川町"]
        )
    ].copy()
    if len(study_municipalities) != 3:
        raise ValueError("Expected three positive-outage municipalities for map extent")
    projected_bounds = tuple(
        float(value) for value in study_municipalities.total_bounds
    )
    geographic_bounds = tuple(
        float(value)
        for value in study_municipalities.to_crs(6668).total_bounds
    )
    affected = meshes.loc[meshes["Affected"]].copy()
    original_covered = affected.loc[affected["Original Covered"]]
    gained = affected.loc[affected["Coverage Gained"]]
    complete_covered = affected.loc[affected["Complete Covered"]]
    original_finite = affected["Nearest Original Point Network Distance (m)"].notna()
    complete_finite = affected["Nearest Complete Point Network Distance (m)"].notna()
    original_uncovered = affected.loc[~affected["Original Covered"] & original_finite]
    original_undefined = affected.loc[~affected["Original Covered"] & ~original_finite]
    complete_uncovered = affected.loc[~affected["Complete Covered"] & complete_finite]
    complete_undefined = affected.loc[~affected["Complete Covered"] & ~complete_finite]

    total_population = float(affected["Estimated Outage Population"].sum())
    original_covered_population = float(
        original_covered["Estimated Outage Population"].sum()
    )
    complete_covered_population = float(
        complete_covered["Estimated Outage Population"].sum()
    )
    gained_population = float(gained["Estimated Outage Population"].sum())
    original_share = original_covered_population / total_population
    complete_share = complete_covered_population / total_population
    if len(original) != 17 or len(recovered) != 19 or len(water) != 36:
        raise ValueError("Water-point recovery counts no longer match the audited inputs")
    if water["Location Resolution Status"].eq("unmatched").any():
        raise ValueError("An announced water point remains unresolved")
    partition_population = float(
        complete_covered["Estimated Outage Population"].sum()
        + complete_uncovered["Estimated Outage Population"].sum()
        + complete_undefined["Estimated Outage Population"].sum()
    )
    if not np.isclose(partition_population, total_population, rtol=0, atol=1e-6):
        raise ValueError("Access categories do not partition affected population")
    if not (0 <= original_share <= complete_share <= 1):
        raise ValueError("Coverage shares are not ordered within [0, 1]")

    set_theme()
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 9.2), constrained_layout=True)
    map_axes = [axes[0, 0], axes[0, 1], axes[1, 0]]
    key_ax = axes[1, 1]

    # Panel a: location-evidence audit after the announcement search.
    affected.plot(
        ax=map_axes[0], color=AFFECTED_COLOR, edgecolor="none", rasterized=True, zorder=1
    )
    municipalities.boundary.plot(
        ax=map_axes[0], color=BOUNDARY_GREY, linewidth=0.35, zorder=3
    )
    original.plot(
        ax=map_axes[0],
        color=ORIGINAL_COLOR,
        edgecolor="white",
        linewidth=0.45,
        markersize=23,
        zorder=5,
    )
    recovered.plot(
        ax=map_axes[0],
        color=RECOVERED_COLOR,
        edgecolor="white",
        linewidth=0.6,
        marker="^",
        markersize=28,
        zorder=6,
    )
    add_summary(
        map_axes[0],
        "Announced point locations\n"
        f"Previously resolved: {len(original)}\n"
        f"Recovered from announcements: {len(recovered)}\n"
        f"Complete: {len(original) + len(recovered)}/{len(water)}",
    )
    # Panel b: conservative pre-recovery coverage using the original 17 points.
    plot_distance_bands(
        map_axes[1], affected, "Nearest Original Point Network Distance (m)"
    )
    municipalities.boundary.plot(
        ax=map_axes[1], color=BOUNDARY_GREY, linewidth=0.35, zorder=4
    )
    original.plot(
        ax=map_axes[1], color=ORIGINAL_COLOR, edgecolor="white", linewidth=0.4,
        markersize=18, zorder=5
    )
    add_summary(
        map_axes[1],
        "Before location recovery (17 points)\n"
        f"Threshold: {ACCESS_THRESHOLD_M:,.0f} m\n"
        f"Covered: {original_covered_population:,.0f} people ({original_share:.1%})",
    )
    # Panel c: complete-location coverage after recovering all 19 points.
    plot_distance_bands(
        map_axes[2], affected, "Nearest Complete Point Network Distance (m)"
    )
    municipalities.boundary.plot(
        ax=map_axes[2], color=BOUNDARY_GREY, linewidth=0.35, zorder=5
    )
    original.plot(
        ax=map_axes[2], color=ORIGINAL_COLOR, edgecolor="white", linewidth=0.4,
        markersize=18, zorder=6
    )
    recovered.plot(
        ax=map_axes[2], color=RECOVERED_COLOR, edgecolor="white", linewidth=0.4,
        marker="^", markersize=22, zorder=7
    )
    add_summary(
        map_axes[2],
        "After location recovery (36 points)\n"
        f"Covered: {complete_covered_population:,.0f} people ({complete_share:.1%})\n"
        f"Gain: +{gained_population:,.0f} people (+{complete_share - original_share:.1%})",
    )
    for label, ax in zip("abc", map_axes, strict=True):
        style_map(ax, projected_bounds, geographic_bounds)
        add_panel_label(ax, label)
    draw_legend_panel(key_ax)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print(f"Affected population denominator: {total_population:,.3f}")
    print(
        f"Original 17-point 500 m coverage: {original_covered_population:,.3f} "
        f"({original_share:.6%})"
    )
    print(
        f"Complete 36-point 500 m coverage: "
        f"{complete_covered_population:,.3f} ({complete_share:.6%})"
    )
    print(f"Recovered announcement-linked locations: {len(recovered)}")
    print(f"Resolved announced points: {len(original) + len(recovered)}/{len(water)}")
    print("Unresolved announced points: 0")
    print(f"Undefined-distance affected meshes: {len(complete_undefined):,}")
    print(f"Saved: {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
