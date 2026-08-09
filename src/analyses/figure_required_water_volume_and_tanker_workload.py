#!/usr/bin/env python3
"""Required Water Volume and Tanker Workload.

Plan: Compare daily water requirements, route-constrained feasible trips, and
scenario-equivalent tanker requirements across the approved demand and
operational sensitivities.
Framework: AnaSOP Sections 5-7 demand, feasible-trip, deliverable-volume, and
required-tanker equations. Resident and shelter ledgers remain separate. The
fleet panel uses median best-route productivity across announced points and is
a planning workload equivalent, not observed fleet availability or operations.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.patches import Rectangle
from scipy.sparse import bmat, csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

from _figure_style import (
    BLACK,
    BLUE,
    BORDER_GREY,
    GREEN,
    LIGHT_GREY,
    PANEL_FILL,
    VERMILLION,
    panel_label,
    set_theme,
)


ROOT = Path(__file__).resolve().parents[2]
MUNICIPAL_DEMAND = (
    ROOT / "data/processed/municipality_outage_demand_scenarios_preprocessed.parquet"
)
SHELTER_DEMAND = (
    ROOT / "data/processed/shelter_water_demand_network_access_preprocessed.parquet"
)
PARAMETERS = ROOT / "data/processed/emergency_water_scenario_parameters_preprocessed.parquet"
DISPATCH_BASES = (
    ROOT / "data/processed/kumamoto_dispatch_base_network_access_preprocessed.parquet"
)
REFILL_CANDIDATES = (
    ROOT / "data/processed/kumamoto_water_treatment_facilities_2010_preprocessed.parquet"
)
WATER_POINTS = ROOT / "data/processed/emergency_water_points_network_access_preprocessed.parquet"
ROAD_NODES = ROOT / "data/processed/kumamoto_routable_road_nodes_preprocessed.parquet"
ROAD_EDGES = ROOT / "data/processed/kumamoto_routable_road_edges_preprocessed.parquet"
OUTPUT_PATH = ROOT / "data/results/figures/Figure_required_water_volume_and_tanker_workload.png"

PROJECTED_CRS = 6670
CONNECTOR_SPEED_KMH = 20.0
REFILL_SNAP_LIMIT_M = 250.0


def parameter_values(parameters: pd.DataFrame, name: str) -> dict[str, float]:
    selected = parameters.loc[parameters["Parameter Name"].eq(name)].copy()
    selected["value"] = pd.to_numeric(selected["Parameter Value"], errors="coerce")
    if selected["value"].isna().any():
        raise ValueError(f"Nonnumeric value in required parameter: {name}")
    return dict(zip(selected["Scenario Level"].astype(str), selected["value"], strict=True))


def build_time_graph(
    nodes: pd.DataFrame, edges: pd.DataFrame
) -> tuple[csr_matrix, pd.Series, pd.DataFrame]:
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
    retained = retained.dropna(
        subset=["From Index", "To Index", "Baseline Edge Travel Time (min)"]
    )
    retained["From Index"] = retained["From Index"].astype(np.int32)
    retained["To Index"] = retained["To Index"].astype(np.int32)
    retained["Pair A"] = np.minimum(retained["From Index"], retained["To Index"])
    retained["Pair B"] = np.maximum(retained["From Index"], retained["To Index"])
    pairs = retained.groupby(["Pair A", "Pair B"], observed=True, sort=False)[
        "Baseline Edge Travel Time (min)"
    ].min().reset_index()
    rows = np.concatenate(
        [pairs["Pair A"].to_numpy(np.int32), pairs["Pair B"].to_numpy(np.int32)]
    )
    columns = np.concatenate(
        [pairs["Pair B"].to_numpy(np.int32), pairs["Pair A"].to_numpy(np.int32)]
    )
    weights = np.tile(pairs["Baseline Edge Travel Time (min)"].to_numpy(float), 2)
    graph = csr_matrix((weights, (rows, columns)), shape=(len(nodes), len(nodes)))
    return graph, node_index, retained


def nearest_dispatch_base_time(
    graph: csr_matrix,
    retained_edges: pd.DataFrame,
    dispatch_bases: pd.DataFrame,
) -> np.ndarray:
    """Run one shortest-path solve from a super-source connected to all bases."""
    edge_lookup = retained_edges[
        [
            "Road Edge ID",
            "From Index",
            "To Index",
            "Baseline Edge Travel Time (min)",
        ]
    ].drop_duplicates("Road Edge ID")
    bases = dispatch_bases.loc[
        dispatch_bases["Candidate Dispatch Base"].fillna(False)
        & dispatch_bases["Network Snap Accepted"].fillna(False)
    ].merge(
        edge_lookup,
        left_on="Access Road Edge ID",
        right_on="Road Edge ID",
        how="inner",
        validate="many_to_one",
    )
    if bases.empty:
        raise ValueError("No candidate dispatch base links to the baseline graph")
    fraction = pd.to_numeric(bases["Access Edge Fraction"], errors="coerce").clip(0, 1)
    edge_time = pd.to_numeric(
        bases["Baseline Edge Travel Time (min)"], errors="coerce"
    )
    connector_time = (
        pd.to_numeric(bases["Network Snap Distance (m)"], errors="coerce")
        / 1000.0
        / CONNECTOR_SPEED_KMH
        * 60.0
    )
    endpoint_indices = np.concatenate(
        [bases["From Index"].to_numpy(np.int32), bases["To Index"].to_numpy(np.int32)]
    )
    endpoint_offsets = np.concatenate(
        [
            (connector_time + fraction * edge_time).to_numpy(float),
            (connector_time + (1.0 - fraction) * edge_time).to_numpy(float),
        ]
    )
    links = pd.DataFrame({"index": endpoint_indices, "offset": endpoint_offsets})
    links = links.groupby("index", sort=False)["offset"].min()
    super_links = csr_matrix(
        (
            links.to_numpy(float),
            (np.zeros(len(links), dtype=np.int32), links.index.to_numpy(np.int32)),
        ),
        shape=(1, graph.shape[0]),
    )
    augmented = bmat(
        [[graph, super_links.T], [super_links, csr_matrix((1, 1))]], format="csr"
    )
    return dijkstra(
        augmented, directed=False, indices=graph.shape[0], return_predecessors=False
    )[:-1]


def route_time_inputs() -> tuple[np.ndarray, np.ndarray, int]:
    """Return base-to-refill and refill-to-point times for historical candidates."""
    nodes = gpd.read_parquet(ROAD_NODES, columns=["Network Node ID", "Geometry"])
    edges = pd.read_parquet(
        ROAD_EDGES,
        columns=[
            "Road Edge ID",
            "From Node ID",
            "To Node ID",
            "Baseline Edge Travel Time (min)",
            "Road Available",
            "Network Analysis Eligible",
        ],
    )
    graph, node_index, retained = build_time_graph(nodes, edges)
    bases = pd.read_parquet(DISPATCH_BASES)
    base_to_node = nearest_dispatch_base_time(graph, retained, bases)

    projected_nodes = nodes.to_crs(PROJECTED_CRS)
    node_xy = np.column_stack(
        [projected_nodes.geometry.x.to_numpy(), projected_nodes.geometry.y.to_numpy()]
    )
    refill = gpd.read_parquet(REFILL_CANDIDATES)
    if not refill["Historical Capacity Only"].fillna(False).all():
        raise ValueError("A refill candidate is not labeled historical-only")
    projected_refill = refill.to_crs(PROJECTED_CRS)
    snap_distance, snap_index = cKDTree(node_xy).query(
        np.column_stack(
            [projected_refill.geometry.x.to_numpy(), projected_refill.geometry.y.to_numpy()]
        ),
        k=1,
    )
    accepted = (snap_distance <= REFILL_SNAP_LIMIT_M) & np.isfinite(
        base_to_node[snap_index]
    )
    refill_index = snap_index[accepted].astype(np.int32)
    refill_connector = (
        snap_distance[accepted] / 1000.0 / CONNECTOR_SPEED_KMH * 60.0
    )
    base_to_refill = base_to_node[refill_index] + refill_connector
    if not len(refill_index):
        raise ValueError("No historical refill candidate links to a dispatch base")

    water = pd.read_parquet(WATER_POINTS)
    water = water.loc[
        water["Network Snap Accepted"].fillna(False)
        & water["Water Point Node ID"].notna()
    ].copy()
    if len(water) != 36:
        raise ValueError("Expected 36 network-eligible announced water points")
    water_index = water["Water Point Node ID"].astype(str).map(node_index)
    if water_index.isna().any():
        raise ValueError("An announced water point is absent from the road graph")
    water_to_nodes = dijkstra(
        graph,
        directed=False,
        indices=water_index.to_numpy(np.int32),
        return_predecessors=False,
    )
    refill_to_point = water_to_nodes[:, refill_index]
    water_connector = (
        pd.to_numeric(water["Network Snap Distance (m)"], errors="coerce").to_numpy()
        / 1000.0
        / CONNECTOR_SPEED_KMH
        * 60.0
    )
    refill_to_point = (
        refill_to_point + refill_connector[np.newaxis, :] + water_connector[:, np.newaxis]
    )
    return base_to_refill, refill_to_point, len(refill_index)


def best_feasible_trips(
    base_to_refill: np.ndarray,
    refill_to_point: np.ndarray,
    work_hours: float,
    service_minutes: float,
    trip_limit: float,
) -> np.ndarray:
    numerator = 60.0 * work_hours - 2.0 * base_to_refill[np.newaxis, :]
    denominator = 2.0 * refill_to_point + service_minutes
    feasible = np.floor(
        np.divide(
            numerator,
            denominator,
            out=np.zeros_like(denominator),
            where=np.isfinite(denominator) & (denominator > 0),
        )
    )
    feasible = np.minimum(np.maximum(feasible, 0), trip_limit)
    best = feasible.max(axis=1)
    if np.any(best <= 0):
        raise ValueError("At least one announced point has no feasible best route")
    return best


def frame_heatmap(ax: plt.Axes) -> None:
    """Restore the complete frame hidden by seaborn heatmaps."""
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(BORDER_GREY)
        spine.set_linewidth(0.85)


def main() -> None:
    parameters = pd.read_parquet(PARAMETERS)
    capacity = parameter_values(parameters, "Tanker Capacity")
    trip_limit = parameter_values(parameters, "Daily Trip Limit")
    work_limit = parameter_values(parameters, "Daily Work Limit")
    loading = parameter_values(parameters, "Loading Time")
    unloading = parameter_values(parameters, "Unloading Time")

    municipal = pd.read_parquet(MUNICIPAL_DEMAND)
    population_order = [
        "lower_one_person_per_household",
        "proportional_central",
        "upper_p90_household_size",
    ]
    demand_order = ["minimum", "basic", "extended"]
    resident_volume = (
        municipal.groupby(
            ["Outage Population Scenario", "Demand Scenario"], observed=True
        )["Estimated Water Demand (L/day)"].sum().unstack("Demand Scenario")
        .reindex(index=population_order, columns=demand_order)
        / 1000.0
    )
    shelter = pd.read_parquet(SHELTER_DEMAND)
    shelter_volume = (
        shelter.groupby("Demand Scenario", observed=True)[
            "Estimated Shelter Water Demand (L/day)"
        ].sum().reindex(demand_order)
        / 1000.0
    )
    volume = pd.concat(
        [resident_volume, shelter_volume.to_frame().T.rename(index={0: "shelter"})]
    )
    volume.index = ["Resident: lower", "Resident: central", "Resident: upper", "Shelter"]
    volume.columns = ["3 L", "10 L", "20 L"]

    base_to_refill, refill_to_point, refill_count = route_time_inputs()
    work_rows = ["short", "central", "long"]
    service_levels = ["short", "central", "long"]
    service_totals = {
        level: loading[level] + unloading[level] for level in service_levels
    }
    trip_median = pd.DataFrame(
        index=[f"{work_limit[level]:.0f} h" for level in work_rows],
        columns=[f"{service_totals[level]:.0f} min" for level in service_levels],
        dtype=float,
    )
    trip_annotation = trip_median.copy().astype(object)
    for row_level, row_label in zip(work_rows, trip_median.index, strict=True):
        for service_level, column_label in zip(
            service_levels, trip_median.columns, strict=True
        ):
            best = best_feasible_trips(
                base_to_refill,
                refill_to_point,
                work_limit[row_level],
                service_totals[service_level],
                trip_limit["central"],
            )
            trip_median.loc[row_label, column_label] = np.median(best)
            trip_annotation.loc[row_label, column_label] = (
                f"{np.median(best):.0f}\n[{best.min():.0f}-{best.max():.0f}]"
            )

    central_resident_liters = float(
        resident_volume.loc["proportional_central", "minimum"] * 1000.0
    )
    minimum_shelter_liters = float(shelter_volume.loc["minimum"] * 1000.0)
    capacity_rows = ["low", "central", "high"]
    trip_columns = ["low", "central", "high"]
    fleet = pd.DataFrame(
        index=[f"{capacity[level] / 1000:.0f} m3" for level in capacity_rows],
        columns=[f"{trip_limit[level]:.0f} trips" for level in trip_columns],
        dtype=float,
    )
    fleet_annotation = fleet.copy().astype(object)
    for capacity_level, row_label in zip(capacity_rows, fleet.index, strict=True):
        for trip_level, column_label in zip(trip_columns, fleet.columns, strict=True):
            best = best_feasible_trips(
                base_to_refill,
                refill_to_point,
                work_limit["central"],
                loading["central"] + unloading["central"],
                trip_limit[trip_level],
            )
            median_trips = float(np.median(best))
            deliverable = capacity[capacity_level] * median_trips
            resident_fleet = int(np.ceil(central_resident_liters / deliverable))
            shelter_fleet = int(np.ceil(minimum_shelter_liters / deliverable))
            fleet.loc[row_label, column_label] = resident_fleet
            fleet_annotation.loc[row_label, column_label] = (
                f"R {resident_fleet}\nS {shelter_fleet}"
            )

    set_theme()
    fig = plt.figure(figsize=(11.4, 8.2), facecolor="white")
    grid = fig.add_gridspec(
        2,
        2,
        left=0.09,
        right=0.965,
        bottom=0.08,
        top=0.96,
        wspace=0.30,
        hspace=0.34,
    )
    axes = np.array(
        [
            fig.add_subplot(grid[0, 0]),
            fig.add_subplot(grid[0, 1]),
            fig.add_subplot(grid[1, 0]),
        ],
        dtype=object,
    )
    guide_ax = fig.add_subplot(grid[1, 1])

    volume_cmap = LinearSegmentedColormap.from_list(
        "required_volume", ["#F7FBFF", "#9ECAE1", BLUE, BLACK]
    )
    trip_cmap = LinearSegmentedColormap.from_list(
        "feasible_trips", ["#F4FBF8", "#9BD8C4", GREEN, BLACK]
    )
    fleet_cmap = LinearSegmentedColormap.from_list(
        "equivalent_fleet", ["#FFF7EC", "#FDBB84", VERMILLION, BLACK]
    )

    volume_annotation = volume.map(lambda value: f"{value:,.1f}")
    sns.heatmap(
        volume,
        ax=axes[0],
        cmap=volume_cmap,
        norm=LogNorm(vmin=float(volume.min().min()), vmax=float(volume.max().max())),
        annot=volume_annotation,
        fmt="",
        linewidths=0.7,
        linecolor="white",
        cbar_kws={
            "label": "Required volume (m³/day)",
            "shrink": 0.78,
            "pad": 0.025,
            "aspect": 18,
        },
    )
    axes[0].hlines(3, *axes[0].get_xlim(), color="#303030", linewidth=1.4)
    axes[0].set_xlabel("Per-capita demand scenario")
    axes[0].set_ylabel("")

    sns.heatmap(
        trip_median,
        ax=axes[1],
        cmap=trip_cmap,
        vmin=0,
        vmax=trip_limit["central"],
        annot=trip_annotation,
        fmt="",
        linewidths=0.7,
        linecolor="white",
        cbar_kws={
            "label": "Median feasible trips/tanker/day",
            "shrink": 0.78,
            "pad": 0.025,
            "aspect": 18,
        },
    )
    axes[1].set_xlabel("Loading + unloading time")
    axes[1].set_ylabel("Daily work limit")

    sns.heatmap(
        fleet,
        ax=axes[2],
        cmap=fleet_cmap,
        annot=fleet_annotation,
        fmt="",
        linewidths=0.7,
        linecolor="white",
        cbar_kws={
            "label": "Resident-equivalent vehicles",
            "shrink": 0.78,
            "pad": 0.025,
            "aspect": 18,
        },
    )
    axes[2].set_xlabel("Daily trip limit")
    axes[2].set_ylabel("Tanker capacity")

    for label, ax in zip("abc", axes, strict=True):
        panel_label(ax, label, x=-0.09, y=1.055)
        frame_heatmap(ax)
        ax.tick_params(axis="x", rotation=0)
        ax.tick_params(axis="y", rotation=0)

    guide_ax.set_xlim(0, 1)
    guide_ax.set_ylim(0, 1)
    guide_ax.axis("off")
    guide_ax.add_patch(
        Rectangle(
            (0.02, 0.08),
            0.94,
            0.84,
            facecolor=PANEL_FILL,
            edgecolor=BORDER_GREY,
            linewidth=0.85,
        )
    )
    guide_ax.text(
        0.08, 0.84, "Reading guide", fontsize=10.5, fontweight="bold", va="top"
    )
    guide_rows = [
        (BLUE, "a", "Required water volume (m³/day)\nResident and shelter ledgers remain separate."),
        (GREEN, "b", f"Median feasible trips [minimum–maximum]\nAcross 36 points; daily trip cap = {trip_limit['central']:.0f}."),
        (VERMILLION, "c", "Equivalent vehicles required\nR = residents; S = shelter evacuees."),
    ]
    for y, (color, label, description) in zip(
        [0.68, 0.49, 0.30], guide_rows, strict=True
    ):
        guide_ax.add_patch(
            Rectangle((0.08, y - 0.012), 0.035, 0.035, facecolor=color, edgecolor="none")
        )
        guide_ax.text(
            0.135,
            y + 0.005,
            f"{label}  {description}",
            fontsize=8.2,
            va="center",
            linespacing=1.25,
        )
    guide_ax.plot([0.08, 0.90], [0.19, 0.19], color=LIGHT_GREY, linewidth=1.0)
    guide_ax.text(
        0.08,
        0.16,
        "Panel c: central affected population; 3 L/person/day; 10 h workday;\n"
        "60 min service. Planning requirement—not observed availability or deliveries.",
        fontsize=7.4,
        va="top",
        color=BLACK,
        linespacing=1.25,
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print(f"Resident central minimum demand: {central_resident_liters / 1000:,.3f} m3/day")
    print(f"Shelter minimum demand (separate): {minimum_shelter_liters / 1000:,.3f} m3/day")
    print(f"Network-linked historical refill candidates: {refill_count}")
    print("Primary equivalent fleet cell (3 m3, 5 trips): "
          f"{fleet_annotation.loc['3 m3', '5 trips'].replace(chr(10), ', ')}")
    print(f"Saved: {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
