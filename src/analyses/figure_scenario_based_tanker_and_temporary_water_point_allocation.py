#!/usr/bin/env python3
"""Scenario-Based Tanker and Temporary Water-Point Allocation.

Plan: Map resident-ledger access ceilings, pooled multi-site tanker trips,
selected temporary water points, historical refill candidates, schematic support
bases, and fleet gaps across matched 500, 1,000, and 2,000 m allocation
catchments.
Framework: AnaSOP Sections 5-7 central/minimum resident demand,
route-constrained refill-pool trip and uniform 10-hour logistics-shift budgets,
a 10-vehicle available fleet, and lexicographic unmet-demand then operational-
efficiency allocation. The three panels hold the no-modeled-closure road and
operational states fixed to reveal the shift from access-constrained to
capacity-constrained allocation. The 2,000 m catchment is an extended planning
diagnostic, not a walking standard. Historical refill candidates remain scenario
evidence, not verified 2026 operating facilities.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Patch
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix, csr_matrix, vstack
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
from shapely.geometry import box

from figure_outage_population_and_emergency_water_demand import style_map
from figure_required_water_volume_and_tanker_workload import parameter_values


ROOT = Path(__file__).resolve().parents[2]
MESH_DEMAND = ROOT / "data/processed/population_mesh_outage_demand_scenarios_preprocessed.parquet"
MESH_ACCESS = ROOT / "data/processed/kumamoto_population_mesh_network_access_preprocessed.parquet"
OLDER_GROUPS = ROOT / "data/processed/kumamoto_population_disclosure_groups_preprocessed.parquet"
OLDER_ACCESS = ROOT / "data/processed/kumamoto_population_group_network_access_preprocessed.parquet"
WATER_POINTS = ROOT / "data/processed/emergency_water_points_network_access_preprocessed.parquet"
STAGING = ROOT / "data/processed/kumamoto_staging_site_candidates_preprocessed.parquet"
DISPATCH_BASES = ROOT / "data/processed/kumamoto_dispatch_base_network_access_preprocessed.parquet"
REFILLS = ROOT / "data/processed/kumamoto_water_treatment_facilities_2010_preprocessed.parquet"
ROAD_NODES = ROOT / "data/processed/kumamoto_routable_road_nodes_preprocessed.parquet"
ROAD_EDGES = ROOT / "data/processed/kumamoto_routable_road_edges_preprocessed.parquet"
RESTRICTIONS = ROOT / "data/processed/road_restriction_edge_matches_preprocessed.parquet"
MUNICIPALITIES = ROOT / "data/processed/kumamoto_reporting_municipalities_preprocessed.parquet"
PARAMETERS = ROOT / "data/processed/emergency_water_scenario_parameters_preprocessed.parquet"
OUTPUT_PATH = ROOT / "data/results/figures/Figure_scenario_based_tanker_and_temporary_water_point_allocation.png"
SOLVER_AUDIT_PATH = ROOT / "data/exp/allocation_solver_audit.json"

PROJECTED_CRS = 6670
ACCESS_DISTANCE_M = 500.0
EXTENDED_ACCESS_DISTANCE_M = 5000.0
CONNECTOR_SPEED_KMH = 20.0
REFILL_SNAP_LIMIT_M = 250.0
ROUTES_PER_SITE = 3
SITE_COLOR = "#111827"
TEMP_COLOR = "#f77f00"
REFILL_COLOR = "#7b2cbf"
BASE_COLOR = "#222222"
FLEET_GAP_COLOR = "#f3c892"
DISTANCE_BANDS = [0.0, 250.0, 500.0, 1000.0, 2000.0, 5000.0, np.inf]
DISTANCE_LABELS = [
    "<=250 m",
    "250-500 m",
    "500-1,000 m",
    "1,000-2,000 m",
    "2,000-5,000 m",
    ">5,000 m or unreachable",
]
DISTANCE_COLORS = {
    "<=250 m": "#0072B2",
    "250-500 m": "#009E73",
    "500-1,000 m": "#F0E442",
    "1,000-2,000 m": "#D55E00",
    "2,000-5,000 m": "#CC79A7",
    ">5,000 m or unreachable": "#eceff1",
}
PRIMARY_MIP_GAP = 0.01
PHYSICAL_BOUND_GAP = 0.002
OPERATIONAL_MIP_GAP = 1e-6
OPERATIONAL_TIME_LIMIT_SECONDS = 900.0


@dataclass
class ScenarioInputs:
    label: str
    units: gpd.GeoDataFrame
    sites: gpd.GeoDataFrame
    arcs: pd.DataFrame
    extended_arcs: pd.DataFrame
    route_site_index: np.ndarray
    route_refill_index: np.ndarray
    route_cycle_minutes: np.ndarray
    refill_base_minutes: np.ndarray
    trip_capacity_liters: float
    trip_limit: int
    work_minutes: float
    refills: gpd.GeoDataFrame
    dispatch_bases: gpd.GeoDataFrame
    closed_edge_count: int


@dataclass
class AllocationResult:
    delivery_liters: float
    route_trips: np.ndarray
    trips_by_site: np.ndarray
    vehicles_by_refill: np.ndarray
    selected_arcs: pd.DataFrame
    selected_sites: gpd.GeoDataFrame
    failed_point: str | None
    solver_audit: tuple[dict[str, object], ...]

    @property
    def trips_used(self) -> int:
        return int(self.trips_by_site.sum())

    @property
    def fleet_used(self) -> int:
        return int(self.vehicles_by_refill.sum())


def accepted_milp_result(
    result: object,
    stage: str,
    maximum_gap: float,
    physical_upper_bound: float | None = None,
    incumbent_value: float | None = None,
) -> dict[str, object]:
    """Require an auditable incumbent rather than silently accepting a timeout."""
    solution = getattr(result, "x", None)
    status = int(getattr(result, "status", -1))
    gap_value = getattr(result, "mip_gap", None)
    gap = float(gap_value) if gap_value is not None else np.inf
    physical_gap = None
    if physical_upper_bound is not None and incumbent_value is not None:
        physical_gap = (
            max(0.0, physical_upper_bound - incumbent_value) / physical_upper_bound
            if physical_upper_bound > 0
            else 0.0
        )
    solver_gap_accepted = np.isfinite(gap) and gap <= maximum_gap
    physical_gap_accepted = (
        physical_gap is not None and physical_gap <= PHYSICAL_BOUND_GAP
    )
    if (
        solution is None
        or status not in {0, 1}
        or not (solver_gap_accepted or physical_gap_accepted)
    ):
        raise RuntimeError(
            f"{stage} MILP did not meet the publication rule: "
            f"status={status}; gap={gap}; maximum_gap={maximum_gap}; "
            f"physical_gap={physical_gap}; "
            f"message={getattr(result, 'message', 'unavailable')}"
        )
    return {
        "stage": stage,
        "status": status,
        "success": bool(getattr(result, "success", False)),
        "message": str(getattr(result, "message", "")),
        "objective": float(getattr(result, "fun", np.nan)),
        "mip_gap": gap,
        "mip_node_count": int(getattr(result, "mip_node_count", -1)),
        "physical_upper_bound_liters": physical_upper_bound,
        "physical_bound_gap": physical_gap,
        "acceptance_basis": (
            "solver_gap" if solver_gap_accepted else "physical_capacity_bound"
        ),
    }


def build_graphs(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    closed_edges: set[str],
) -> tuple[csr_matrix, csr_matrix, pd.Series, pd.DataFrame]:
    node_index = pd.Series(
        np.arange(len(nodes), dtype=np.int32),
        index=nodes["Network Node ID"].astype(str),
    )
    retained = edges.loc[
        edges["Road Available"].fillna(False)
        & edges["Network Analysis Eligible"].fillna(False)
        & ~edges["Road Edge ID"].astype(str).isin(closed_edges)
    ].copy()
    retained["From Index"] = retained["From Node ID"].astype(str).map(node_index)
    retained["To Index"] = retained["To Node ID"].astype(str).map(node_index)
    retained = retained.dropna(
        subset=[
            "From Index",
            "To Index",
            "Road Length (m)",
            "Baseline Edge Travel Time (min)",
        ]
    )
    retained["From Index"] = retained["From Index"].astype(np.int32)
    retained["To Index"] = retained["To Index"].astype(np.int32)
    retained["Pair A"] = np.minimum(retained["From Index"], retained["To Index"])
    retained["Pair B"] = np.maximum(retained["From Index"], retained["To Index"])
    pairs = retained.groupby(["Pair A", "Pair B"], observed=True, sort=False).agg(
        {"Road Length (m)": "min", "Baseline Edge Travel Time (min)": "min"}
    ).reset_index()
    row = np.concatenate(
        [pairs["Pair A"].to_numpy(np.int32), pairs["Pair B"].to_numpy(np.int32)]
    )
    column = np.concatenate(
        [pairs["Pair B"].to_numpy(np.int32), pairs["Pair A"].to_numpy(np.int32)]
    )
    shape = (len(nodes), len(nodes))
    length_graph = csr_matrix(
        (np.tile(pairs["Road Length (m)"].to_numpy(float), 2), (row, column)),
        shape=shape,
    )
    time_graph = csr_matrix(
        (
            np.tile(pairs["Baseline Edge Travel Time (min)"].to_numpy(float), 2),
            (row, column),
        ),
        shape=shape,
    )
    return length_graph, time_graph, node_index, retained


def edge_lookup(retained: pd.DataFrame) -> pd.DataFrame:
    return retained[
        [
            "Road Edge ID",
            "From Index",
            "To Index",
            "Road Length (m)",
            "Baseline Edge Travel Time (min)",
        ]
    ].drop_duplicates("Road Edge ID")


def site_inventory(
    water: gpd.GeoDataFrame,
    staging: gpd.GeoDataFrame,
    access: pd.DataFrame,
    retained: pd.DataFrame,
    node_index: pd.Series,
    failed_point: str | None,
) -> gpd.GeoDataFrame:
    water = water.loc[
        water["Network Snap Accepted"].fillna(False)
        & water["Water Point Node ID"].notna()
    ].copy()
    if failed_point is not None:
        water = water.loc[water["Water Point Name"].ne(failed_point)].copy()
    water["Site ID"] = "WATER::" + water.index.astype(str)
    water["Site Name"] = water["Water Point Name"].astype(str)
    water["Temporary Site"] = False
    water["Source Node"] = water["Water Point Node ID"].astype(str).map(node_index)
    water["Site Connector Distance (m)"] = pd.to_numeric(
        water["Network Snap Distance (m)"], errors="coerce"
    )

    candidates = staging.loc[
        staging["Screened Staging Candidate"].fillna(False)
        & staging["Candidate Network Eligible"].fillna(False)
        & staging["Network Snap Accepted"].fillna(False)
    ].copy()
    candidate_access = access[
        ["Demand Node ID", "Access Road Edge ID", "Access Edge Fraction"]
    ].drop_duplicates("Demand Node ID")
    candidates = candidates.merge(
        candidate_access,
        left_on="Staging Demand Node ID",
        right_on="Demand Node ID",
        how="inner",
        validate="many_to_one",
    ).merge(
        edge_lookup(retained),
        left_on="Access Road Edge ID",
        right_on="Road Edge ID",
        how="inner",
        validate="many_to_one",
    )
    fraction = pd.to_numeric(candidates["Access Edge Fraction"], errors="coerce").clip(0, 1)
    use_from = fraction.le(0.5)
    candidates["Source Node"] = np.where(
        use_from, candidates["From Index"], candidates["To Index"]
    ).astype(np.int32)
    along = np.where(
        use_from,
        fraction * candidates["Road Length (m)"],
        (1.0 - fraction) * candidates["Road Length (m)"],
    )
    candidates["Site Connector Distance (m)"] = (
        pd.to_numeric(
            candidates["Staging Access Network Snap Distance (m)"], errors="coerce"
        ).fillna(0)
        + along
    )
    candidates["Site ID"] = candidates["Candidate Staging Site ID"].astype(str)
    candidates["Site Name"] = candidates["Candidate Staging Site Name"].fillna(
        candidates["Candidate Staging Site Type"]
    ).astype(str)
    candidates["Temporary Site"] = True

    sites = pd.concat(
        [
            water[
                [
                    "Site ID", "Site Name", "Temporary Site", "Source Node",
                    "Site Connector Distance (m)", "Geometry",
                ]
            ],
            candidates[
                [
                    "Site ID", "Site Name", "Temporary Site", "Source Node",
                    "Site Connector Distance (m)", "Geometry",
                ]
            ],
        ],
        ignore_index=True,
    )
    sites["Source Node"] = pd.to_numeric(sites["Source Node"], errors="coerce")
    sites = sites.dropna(subset=["Source Node", "Geometry"]).sort_values(
        "Site ID", kind="stable"
    ).reset_index(drop=True)
    sites["Source Node"] = sites["Source Node"].astype(np.int32)
    return gpd.GeoDataFrame(sites, geometry="Geometry", crs=water.crs)


def demand_units(
    demand: gpd.GeoDataFrame,
    access: pd.DataFrame,
    retained: pd.DataFrame,
    older_weight: pd.Series,
) -> gpd.GeoDataFrame:
    units = demand.loc[
        demand["Outage Population Scenario"].eq("proportional_central")
        & demand["Demand Scenario"].eq("minimum")
        & demand["Estimated Water Demand (L/day)"].gt(0)
    ].copy()
    units["Mesh Code"] = units["Mesh Code"].astype(str)
    access = access.copy()
    access["Mesh Code"] = access["Mesh Code"].astype(str)
    units = units.merge(
        access[
            [
                "Mesh Code", "Network Snap Distance (m)", "Network Snap Accepted",
                "Access Road Edge ID", "Access Edge Fraction",
            ]
        ],
        on="Mesh Code",
        how="left",
        validate="one_to_one",
    ).merge(
        edge_lookup(retained),
        left_on="Access Road Edge ID",
        right_on="Road Edge ID",
        how="left",
        validate="many_to_one",
    )
    units["Older Priority Population"] = (
        units["Mesh Code"].map(older_weight).fillna(0).astype(float)
    )
    units = units.sort_values("Mesh Code", kind="stable").reset_index(drop=True)
    return gpd.GeoDataFrame(units, geometry="Geometry", crs=demand.crs)


def distance_arcs(
    length_graph: csr_matrix,
    sites: gpd.GeoDataFrame,
    units: gpd.GeoDataFrame,
    access_distance_m: float = ACCESS_DISTANCE_M,
) -> pd.DataFrame:
    distances = dijkstra(
        length_graph,
        directed=False,
        indices=sites["Source Node"].to_numpy(np.int32),
        return_predecessors=False,
    )
    accessible = (
        units["From Index"].notna()
        & units["To Index"].notna()
        & units["Road Length (m)"].notna()
    )
    accessible_index = np.flatnonzero(accessible.to_numpy(bool))
    if not len(accessible_index):
        raise ValueError("No resident demand unit retains a road-access connector")
    linked = units.iloc[accessible_index]
    fraction = pd.to_numeric(
        linked["Access Edge Fraction"], errors="coerce"
    ).clip(0, 1)
    length = pd.to_numeric(
        linked["Road Length (m)"], errors="coerce"
    ).to_numpy(float)
    from_index = linked["From Index"].to_numpy(np.int32)
    to_index = linked["To Index"].to_numpy(np.int32)
    demand_connector = pd.to_numeric(
        linked["Network Snap Distance (m)"], errors="coerce"
    ).to_numpy(float)
    network = np.minimum(
        distances[:, from_index] + fraction.to_numpy(float)[None, :] * length[None, :],
        distances[:, to_index]
        + (1.0 - fraction.to_numpy(float))[None, :] * length[None, :],
    )
    total = (
        network
        + demand_connector[None, :]
        + sites["Site Connector Distance (m)"].to_numpy(float)[:, None]
    )
    site_index, linked_unit_index = np.where(
        np.isfinite(total) & (total <= access_distance_m)
    )
    if not len(site_index):
        raise ValueError("No resident demand is within the approved access distance")
    unit_index = accessible_index[linked_unit_index]
    return pd.DataFrame(
        {
            "Site Index": site_index.astype(np.int32),
            "Unit Index": unit_index.astype(np.int32),
            "Distance (m)": total[site_index, linked_unit_index],
        }
    )


def route_productivity(
    time_graph: csr_matrix,
    sites: gpd.GeoDataFrame,
    nodes: gpd.GeoDataFrame,
    retained: pd.DataFrame,
    parameters: pd.DataFrame,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    float,
    int,
    float,
    gpd.GeoDataFrame,
    gpd.GeoDataFrame,
]:
    projected_nodes = nodes.to_crs(PROJECTED_CRS)
    node_xy = np.column_stack(
        [projected_nodes.geometry.x.to_numpy(), projected_nodes.geometry.y.to_numpy()]
    )
    tree = cKDTree(node_xy)
    refills = gpd.read_parquet(REFILLS).sort_values(
        ["P21 Inspection ID", "Water Treatment Facility Name"],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)
    projected_refills = refills.to_crs(PROJECTED_CRS)
    refill_snap, refill_node = tree.query(
        np.column_stack(
            [projected_refills.geometry.x.to_numpy(), projected_refills.geometry.y.to_numpy()]
        ),
        k=1,
    )
    refill_connector = refill_snap / 1000.0 / CONNECTOR_SPEED_KMH * 60.0

    bases = gpd.read_parquet(DISPATCH_BASES)
    bases = bases.loc[
        bases["Candidate Dispatch Base"].fillna(False)
        & bases["Network Snap Accepted"].fillna(False)
    ].sort_values(
        ["Fire Facility Name", "Address"], kind="stable", na_position="last"
    ).reset_index(drop=True).merge(
        edge_lookup(retained),
        left_on="Access Road Edge ID",
        right_on="Road Edge ID",
        how="inner",
        validate="many_to_one",
    )
    if bases.empty:
        raise ValueError("No dispatch base remains linked in this road state")
    fraction = pd.to_numeric(bases["Access Edge Fraction"], errors="coerce").clip(0, 1)
    use_from = fraction.le(0.5)
    bases["Source Node"] = np.where(
        use_from, bases["From Index"], bases["To Index"]
    ).astype(np.int32)
    bases["Source Offset (min)"] = (
        pd.to_numeric(bases["Network Snap Distance (m)"], errors="coerce")
        / 1000.0
        / CONNECTOR_SPEED_KMH
        * 60.0
        + np.where(
            use_from,
            fraction * bases["Baseline Edge Travel Time (min)"],
            (1.0 - fraction) * bases["Baseline Edge Travel Time (min)"],
        )
    )
    base_distances = dijkstra(
        time_graph,
        directed=False,
        indices=bases["Source Node"].to_numpy(np.int32),
        return_predecessors=False,
    )[:, refill_node]
    base_distances += bases["Source Offset (min)"].to_numpy(float)[:, None]
    base_to_refill = np.min(base_distances, axis=0) + refill_connector
    best_base = np.argmin(base_distances, axis=0)

    accepted_refill = (
        (refill_snap <= REFILL_SNAP_LIMIT_M)
        & np.isfinite(base_to_refill)
        & refills["Historical Capacity Only"].fillna(False).to_numpy(bool)
    )
    refills = refills.loc[accepted_refill].reset_index(drop=True)
    refill_node = refill_node[accepted_refill].astype(np.int32)
    refill_connector = refill_connector[accepted_refill]
    base_to_refill = base_to_refill[accepted_refill]
    best_base = best_base[accepted_refill]
    if not len(refills):
        raise ValueError("No network-linked historical refill candidate remains")

    site_to_refill = dijkstra(
        time_graph,
        directed=False,
        indices=sites["Source Node"].to_numpy(np.int32),
        return_predecessors=False,
    )[:, refill_node]
    site_connector_time = (
        sites["Site Connector Distance (m)"].to_numpy(float)
        / 1000.0
        / CONNECTOR_SPEED_KMH
        * 60.0
    )
    site_to_refill += site_connector_time[:, None] + refill_connector[None, :]

    capacity = float(parameter_values(parameters, "Tanker Capacity")["central"])
    trip_limit = int(parameter_values(parameters, "Daily Trip Limit")["central"])
    work_limit = float(parameter_values(parameters, "Daily Work Limit")["central"])
    work_minutes = 60.0 * work_limit
    service_time = (
        parameter_values(parameters, "Loading Time")["central"]
        + parameter_values(parameters, "Unloading Time")["central"]
    )
    base_minutes = 2.0 * base_to_refill
    cycle_minutes = 2.0 * site_to_refill + service_time
    numerator = work_minutes - base_minutes[None, :]
    denominator = cycle_minutes
    trips = np.floor(
        np.divide(
            numerator,
            denominator,
            out=np.zeros_like(denominator),
            where=np.isfinite(denominator) & (denominator > 0),
        )
    )
    trips = np.minimum(np.maximum(trips, 0), trip_limit)
    effective_minutes = cycle_minutes + base_minutes[None, :] / max(trip_limit, 1)
    effective_minutes[trips < 1] = np.inf

    route_site: list[int] = []
    route_refill: list[int] = []
    route_cycle: list[float] = []
    for site_index in range(len(sites)):
        feasible = np.flatnonzero(np.isfinite(effective_minutes[site_index]))
        if not len(feasible):
            continue
        ordered = feasible[
            np.argsort(effective_minutes[site_index, feasible], kind="stable")
        ][:ROUTES_PER_SITE]
        route_site.extend([site_index] * len(ordered))
        route_refill.extend(ordered.tolist())
        route_cycle.extend(cycle_minutes[site_index, ordered].tolist())

    if not route_site:
        raise ValueError("No feasible refill-to-point trip route remains")
    refills["Supporting Base Row"] = best_base
    return (
        np.asarray(route_site, dtype=np.int32),
        np.asarray(route_refill, dtype=np.int32),
        np.asarray(route_cycle, dtype=float),
        np.asarray(base_minutes, dtype=float),
        capacity,
        trip_limit,
        work_minutes,
        refills,
        bases,
    )


def older_priority_weights() -> pd.Series:
    groups = pd.read_parquet(
        OLDER_GROUPS, columns=["Disclosure Group Code", "Population Age 65+"]
    )
    access = pd.read_parquet(
        OLDER_ACCESS, columns=["Disclosure Group Code", "Representative Mesh Code"]
    )
    linked = groups.merge(access, on="Disclosure Group Code", validate="one_to_one")
    linked["Representative Mesh Code"] = linked["Representative Mesh Code"].astype(str)
    return linked.groupby("Representative Mesh Code")["Population Age 65+"].sum()


def prepare_scenario(
    label: str,
    closed_edges: set[str],
    failed_point: str | None,
    nodes: gpd.GeoDataFrame,
    edges: pd.DataFrame,
    demand: gpd.GeoDataFrame,
    access: pd.DataFrame,
    water: gpd.GeoDataFrame,
    staging: gpd.GeoDataFrame,
    parameters: pd.DataFrame,
    older_weight: pd.Series,
    access_distance_m: float = ACCESS_DISTANCE_M,
) -> ScenarioInputs:
    length_graph, time_graph, node_index, retained = build_graphs(
        nodes, edges, closed_edges
    )
    units = demand_units(demand, access, retained, older_weight)
    sites = site_inventory(
        water, staging, access, retained, node_index, failed_point
    )
    extended_arcs = distance_arcs(
        length_graph, sites, units, EXTENDED_ACCESS_DISTANCE_M
    )
    arcs = extended_arcs.loc[
        extended_arcs["Distance (m)"].le(access_distance_m)
    ].copy()
    (
        route_site,
        route_refill,
        route_cycle,
        base_minutes,
        trip_capacity,
        trip_limit,
        work_minutes,
        refills,
        bases,
    ) = route_productivity(time_graph, sites, nodes, retained, parameters)
    feasible_site = np.zeros(len(sites), dtype=bool)
    feasible_site[np.unique(route_site)] = True
    arcs = arcs.loc[
        feasible_site[arcs["Site Index"].to_numpy(np.int32)]
    ].reset_index(drop=True)
    extended_arcs = extended_arcs.loc[
        feasible_site[extended_arcs["Site Index"].to_numpy(np.int32)]
    ].reset_index(drop=True)
    return ScenarioInputs(
        label,
        units,
        sites,
        arcs,
        extended_arcs,
        route_site,
        route_refill,
        route_cycle,
        base_minutes,
        trip_capacity,
        trip_limit,
        work_minutes,
        refills,
        bases,
        len(closed_edges),
    )


def solve_allocation(
    scenario: ScenarioInputs,
    fleet_size: int,
    failed_point: str | None = None,
    refine: bool = True,
    temporary_site_budget: int | None = None,
) -> AllocationResult:
    arcs = scenario.arcs.copy()
    units = scenario.units
    sites = scenario.sites
    arc_count = len(arcs)
    site_count = len(sites)
    route_count = len(scenario.route_site_index)
    refill_count = len(scenario.refills)
    temp_sites = np.flatnonzero(sites["Temporary Site"].to_numpy(bool))
    temp_count = len(temp_sites)
    if temporary_site_budget is not None and temporary_site_budget < 0:
        raise ValueError("Temporary-site budget must be nonnegative")
    route_offset = arc_count
    vehicle_offset = route_offset + route_count
    temp_offset = vehicle_offset + refill_count
    variable_count = temp_offset + temp_count

    demand = units["Estimated Water Demand (L/day)"].to_numpy(float)
    arc_demand = demand[arcs["Unit Index"].to_numpy(np.int32)]
    rows: list[np.ndarray] = []
    cols: list[np.ndarray] = []
    data: list[np.ndarray] = []
    upper: list[np.ndarray] = []
    lower: list[np.ndarray] = []
    row_offset = 0

    rows.append(arcs["Unit Index"].to_numpy(np.int32) + row_offset)
    cols.append(np.arange(arc_count, dtype=np.int32))
    data.append(np.ones(arc_count))
    lower.append(np.full(len(units), -np.inf))
    upper.append(np.ones(len(units)))
    row_offset += len(units)

    # Water assigned at a point cannot exceed the capacity of its planned trips.
    rows.append(arcs["Site Index"].to_numpy(np.int32) + row_offset)
    cols.append(np.arange(arc_count, dtype=np.int32))
    data.append(arc_demand)
    rows.append(scenario.route_site_index + row_offset)
    cols.append(route_offset + np.arange(route_count, dtype=np.int32))
    data.append(np.full(route_count, -scenario.trip_capacity_liters))
    lower.append(np.full(site_count, -np.inf))
    upper.append(np.zeros(site_count))
    row_offset += site_count

    # Each refill pool can distribute its tankers across several points, subject
    # to both the daily trip cap and the pooled daily work-time budget.
    rows.append(scenario.route_refill_index + row_offset)
    cols.append(route_offset + np.arange(route_count, dtype=np.int32))
    data.append(np.ones(route_count))
    rows.append(np.arange(refill_count, dtype=np.int32) + row_offset)
    cols.append(vehicle_offset + np.arange(refill_count, dtype=np.int32))
    data.append(np.full(refill_count, -float(scenario.trip_limit)))
    lower.append(np.full(refill_count, -np.inf))
    upper.append(np.zeros(refill_count))
    row_offset += refill_count

    rows.append(scenario.route_refill_index + row_offset)
    cols.append(route_offset + np.arange(route_count, dtype=np.int32))
    data.append(scenario.route_cycle_minutes)
    rows.append(np.arange(refill_count, dtype=np.int32) + row_offset)
    cols.append(vehicle_offset + np.arange(refill_count, dtype=np.int32))
    data.append(scenario.refill_base_minutes - scenario.work_minutes)
    lower.append(np.full(refill_count, -np.inf))
    upper.append(np.zeros(refill_count))
    row_offset += refill_count

    rows.append(np.full(refill_count, row_offset, dtype=np.int32))
    cols.append(vehicle_offset + np.arange(refill_count, dtype=np.int32))
    data.append(np.ones(refill_count))
    lower.append(np.asarray([-np.inf]))
    upper.append(np.asarray([float(fleet_size)]))
    row_offset += 1

    for temp_row, site_index in enumerate(temp_sites):
        route_rows = np.flatnonzero(scenario.route_site_index == site_index)
        rows.append(np.full(len(route_rows) + 1, row_offset, dtype=np.int32))
        cols.append(
            np.concatenate(
                [route_offset + route_rows, np.asarray([temp_offset + temp_row])]
            ).astype(np.int32)
        )
        data.append(
            np.concatenate(
                [
                    np.ones(len(route_rows)),
                    np.asarray([-float(fleet_size * scenario.trip_limit)]),
                ]
            )
        )
        lower.append(np.asarray([-np.inf]))
        upper.append(np.asarray([0.0]))
        row_offset += 1

    if temporary_site_budget is not None and temp_count:
        rows.append(np.full(temp_count, row_offset, dtype=np.int32))
        cols.append(temp_offset + np.arange(temp_count, dtype=np.int32))
        data.append(np.ones(temp_count))
        lower.append(np.asarray([-np.inf]))
        upper.append(np.asarray([float(temporary_site_budget)]))
        row_offset += 1

    matrix = coo_matrix(
        (np.concatenate(data), (np.concatenate(rows), np.concatenate(cols))),
        shape=(row_offset, variable_count),
    ).tocsr()
    lower_bound = np.concatenate(lower)
    upper_bound = np.concatenate(upper)
    bounds_lower = np.zeros(variable_count)
    bounds_upper = np.ones(variable_count)
    bounds_upper[route_offset : route_offset + route_count] = float(
        fleet_size * scenario.trip_limit
    )
    bounds_upper[vehicle_offset : vehicle_offset + refill_count] = float(fleet_size)
    integrality = np.ones(variable_count, dtype=np.int8)

    solver_audit: list[dict[str, object]] = []

    primary_cost = np.zeros(variable_count)
    primary_cost[:arc_count] = -arc_demand
    primary = milp(
        primary_cost,
        integrality=integrality,
        bounds=Bounds(bounds_lower, bounds_upper),
        constraints=LinearConstraint(matrix, lower_bound, upper_bound),
        options={
            "time_limit": 300.0,
            "mip_rel_gap": PRIMARY_MIP_GAP,
            "presolve": True,
        },
    )
    if primary.x is None:
        raise RuntimeError(
            f"Protected-demand MILP returned no incumbent for {scenario.label}: "
            f"{primary.message}"
        )
    delivered = float(np.dot(arc_demand, np.rint(primary.x[:arc_count])))
    accessible_units = np.unique(arcs["Unit Index"].to_numpy(np.int32))
    accessible_demand = float(demand[accessible_units].sum())
    physical_upper_bound = min(
        accessible_demand,
        float(fleet_size * scenario.trip_limit) * scenario.trip_capacity_liters,
    )
    solver_audit.append(
        accepted_milp_result(
            primary,
            "protected-demand",
            PRIMARY_MIP_GAP,
            physical_upper_bound=physical_upper_bound,
            incumbent_value=delivered,
        )
    )
    solution = primary

    if refine:
        def solve_stage(
            cost: np.ndarray,
            stage: str,
            stage_matrix: csr_matrix,
            stage_lower: np.ndarray,
            stage_upper: np.ndarray,
            maximum_gap: float,
            time_limit: float = 120.0,
        ) -> object:
            stage_result = milp(
                cost,
                integrality=integrality,
                bounds=Bounds(bounds_lower, bounds_upper),
                constraints=LinearConstraint(
                    stage_matrix, stage_lower, stage_upper
                ),
                options={
                    "time_limit": time_limit,
                    "mip_rel_gap": maximum_gap,
                    "presolve": True,
                },
            )
            solver_audit.append(
                accepted_milp_result(stage_result, stage, maximum_gap)
            )
            return stage_result

        delivery_row = csr_matrix(
            (
                arc_demand,
                (np.zeros(arc_count, dtype=np.int32), np.arange(arc_count, dtype=np.int32)),
            ),
            shape=(1, variable_count),
        )
        stage_matrix = vstack([matrix, delivery_row], format="csr")
        stage_lower = np.concatenate([lower_bound, [delivered - 1e-4]])
        stage_upper = np.concatenate([upper_bound, [np.inf]])

        maximum_trips = int(fleet_size * scenario.trip_limit)
        maximum_selected_temporary_sites = min(temp_count, maximum_trips)
        trip_weight = float(maximum_selected_temporary_sites + 1)
        vehicle_weight = float((maximum_trips + 1) * trip_weight)
        operational_cost = np.zeros(variable_count)
        operational_cost[
            vehicle_offset : vehicle_offset + refill_count
        ] = vehicle_weight
        operational_cost[
            route_offset : route_offset + route_count
        ] = trip_weight
        if temp_count:
            operational_cost[temp_offset:] = 1.0
        solution = solve_stage(
            operational_cost,
            "bounded-lexicographic-operations",
            stage_matrix,
            stage_lower,
            stage_upper,
            OPERATIONAL_MIP_GAP,
            time_limit=OPERATIONAL_TIME_LIMIT_SECONDS,
        )

    selected_mask = np.rint(solution.x[:arc_count]).astype(bool)
    selected_arcs = arcs.loc[selected_mask].copy()
    route_trips = np.rint(
        solution.x[route_offset : route_offset + route_count]
    ).astype(int)
    vehicles = np.rint(
        solution.x[vehicle_offset : vehicle_offset + refill_count]
    ).astype(int)
    trips_by_site = np.bincount(
        scenario.route_site_index,
        weights=route_trips,
        minlength=site_count,
    ).astype(int)
    selected_indices = np.flatnonzero(trips_by_site > 0)
    selected_sites = sites.loc[selected_indices].copy()
    selected_sites["Trips"] = trips_by_site[selected_indices]
    selected_sites["Site Index"] = selected_indices
    selected_sites["Best Refill Row"] = -1
    for site_index in selected_indices:
        route_rows = np.flatnonzero(
            (scenario.route_site_index == site_index) & (route_trips > 0)
        )
        best_route = route_rows[
            np.lexsort(
                (
                    scenario.route_cycle_minutes[route_rows],
                    -route_trips[route_rows],
                )
            )[0]
        ]
        selected_sites.loc[
            selected_sites["Site Index"].eq(site_index), "Best Refill Row"
        ] = int(scenario.route_refill_index[best_route])
    selected_sites["Best Refill Row"] = selected_sites["Best Refill Row"].astype(int)
    return AllocationResult(
        float(arc_demand[selected_mask].sum()),
        route_trips,
        trips_by_site,
        vehicles,
        selected_arcs,
        selected_sites,
        failed_point,
        tuple(solver_audit),
    )


def validate_solution(
    scenario: ScenarioInputs,
    result: AllocationResult,
    fleet_size: int,
) -> None:
    """Fail loudly if a plotted allocation violates a formal model constraint."""
    demand = scenario.units["Estimated Water Demand (L/day)"].to_numpy(float)
    selected_unit = result.selected_arcs["Unit Index"].to_numpy(np.int32)
    selected_site = result.selected_arcs["Site Index"].to_numpy(np.int32)
    if len(selected_unit) != len(np.unique(selected_unit)):
        raise ValueError("A protected demand mesh is assigned to multiple points")
    assigned_by_site = np.bincount(
        selected_site,
        weights=demand[selected_unit],
        minlength=len(scenario.sites),
    )
    if np.any(
        assigned_by_site
        > scenario.trip_capacity_liters * result.trips_by_site + 1e-5
    ):
        raise ValueError("Point-level assigned demand exceeds planned trip capacity")
    trips_by_refill = np.bincount(
        scenario.route_refill_index,
        weights=result.route_trips,
        minlength=len(scenario.refills),
    )
    if np.any(
        trips_by_refill
        > scenario.trip_limit * result.vehicles_by_refill + 1e-5
    ):
        raise ValueError("Refill-pool trip limit is violated")
    cycle_by_refill = np.bincount(
        scenario.route_refill_index,
        weights=result.route_trips * scenario.route_cycle_minutes,
        minlength=len(scenario.refills),
    )
    used_minutes = (
        cycle_by_refill
        + scenario.refill_base_minutes * result.vehicles_by_refill
    )
    if np.any(
        used_minutes
        > scenario.work_minutes * result.vehicles_by_refill + 1e-5
    ):
        raise ValueError("Refill-pool daily work-time limit is violated")
    if result.fleet_used > fleet_size:
        raise ValueError("Available fleet size is violated")
    if not np.isclose(
        result.delivery_liters, demand[selected_unit].sum(), rtol=0, atol=1e-5
    ):
        raise ValueError("Delivered water does not reconcile to protected demand")


def allocation_signature(
    scenario: ScenarioInputs,
    result: AllocationResult,
) -> dict[str, object]:
    assignments = sorted(
        (
            str(scenario.units.iloc[int(row["Unit Index"])]["Mesh Code"]),
            str(scenario.sites.iloc[int(row["Site Index"])]["Site ID"]),
        )
        for _, row in result.selected_arcs.iterrows()
    )
    route_plan = sorted(
        (
            str(scenario.sites.iloc[int(scenario.route_site_index[index])]["Site ID"]),
            str(
                scenario.refills.iloc[int(scenario.route_refill_index[index])][
                    "P21 Inspection ID"
                ]
            ),
            int(trips),
        )
        for index, trips in enumerate(result.route_trips)
        if int(trips) > 0
    )
    vehicle_plan = sorted(
        (
            str(scenario.refills.iloc[index]["P21 Inspection ID"]),
            int(vehicles),
        )
        for index, vehicles in enumerate(result.vehicles_by_refill)
        if int(vehicles) > 0
    )
    return {
        "delivery_liters": round(float(result.delivery_liters), 6),
        "fleet_used": result.fleet_used,
        "trips_used": result.trips_used,
        "temporary_sites": int(result.selected_sites["Temporary Site"].sum()),
        "selected_site_ids": sorted(result.selected_sites["Site ID"].astype(str)),
        "assignments": assignments,
        "route_plan": route_plan,
        "vehicle_plan": vehicle_plan,
    }


def remove_announced_site(
    baseline: ScenarioInputs, site_index: int
) -> ScenarioInputs:
    """Create a point-failure scenario without recomputing the unchanged graph."""
    keep = np.ones(len(baseline.sites), dtype=bool)
    keep[site_index] = False
    mapping = np.full(len(baseline.sites), -1, dtype=np.int32)
    mapping[np.flatnonzero(keep)] = np.arange(int(keep.sum()), dtype=np.int32)
    arcs = baseline.arcs.loc[
        baseline.arcs["Site Index"].ne(site_index)
    ].copy()
    arcs["Site Index"] = mapping[arcs["Site Index"].to_numpy(np.int32)]
    extended_arcs = baseline.extended_arcs.loc[
        baseline.extended_arcs["Site Index"].ne(site_index)
    ].copy()
    extended_arcs["Site Index"] = mapping[
        extended_arcs["Site Index"].to_numpy(np.int32)
    ]
    keep_route = baseline.route_site_index != site_index
    return ScenarioInputs(
        "High-load announced-point failure screen",
        baseline.units,
        baseline.sites.loc[keep].reset_index(drop=True),
        arcs.reset_index(drop=True),
        extended_arcs.reset_index(drop=True),
        mapping[baseline.route_site_index[keep_route]],
        baseline.route_refill_index[keep_route],
        baseline.route_cycle_minutes[keep_route],
        baseline.refill_base_minutes,
        baseline.trip_capacity_liters,
        baseline.trip_limit,
        baseline.work_minutes,
        baseline.refills,
        baseline.dispatch_bases,
        baseline.closed_edge_count,
    )


def add_panel(
    ax: plt.Axes,
    scenario: ScenarioInputs,
    result: AllocationResult,
    fleet_size: int,
    municipalities: gpd.GeoDataFrame,
    projected_bounds: tuple[float, float, float, float],
    geographic_bounds: tuple[float, float, float, float],
) -> None:
    units = scenario.units.to_crs(PROJECTED_CRS)
    served_units = np.unique(result.selected_arcs["Unit Index"].to_numpy(np.int32))
    accessible_units = np.unique(scenario.arcs["Unit Index"].to_numpy(np.int32))
    nearest_distance = scenario.extended_arcs.groupby("Unit Index", observed=True)[
        "Distance (m)"
    ].min()
    units["Nearest Eligible Point Distance (m)"] = (
        units.index.to_series().map(nearest_distance).fillna(np.inf)
    )
    units["Distance Band"] = pd.cut(
        units["Nearest Eligible Point Distance (m)"],
        bins=DISTANCE_BANDS,
        labels=DISTANCE_LABELS,
        include_lowest=True,
        right=True,
    )
    for distance_label in DISTANCE_LABELS:
        band = units.loc[units["Distance Band"].eq(distance_label)]
        if len(band):
            band.plot(
                ax=ax,
                color=DISTANCE_COLORS[distance_label],
                edgecolor="none",
                rasterized=True,
                zorder=1,
            )
    fleet_gap = units.loc[
        units.index.isin(accessible_units) & ~units.index.isin(served_units)
    ]
    if len(fleet_gap):
        fleet_gap.plot(
            ax=ax,
            color=FLEET_GAP_COLOR,
            edgecolor="#b56a21",
            linewidth=0.15,
            rasterized=True,
            zorder=2,
        )
    municipalities.boundary.plot(ax=ax, color="#4d4d4d", linewidth=0.35, zorder=4)

    selected = result.selected_sites.to_crs(PROJECTED_CRS)
    existing = selected.loc[~selected["Temporary Site"]]
    temporary = selected.loc[selected["Temporary Site"]]
    if len(existing):
        existing.plot(
            ax=ax, color=SITE_COLOR, edgecolor="white", linewidth=0.7,
            markersize=20 + 10 * existing["Trips"].to_numpy(float), zorder=8
        )
    if len(temporary):
        temporary.plot(
            ax=ax, color=TEMP_COLOR, edgecolor="white", linewidth=0.7,
            marker="*", markersize=38 + 14 * temporary["Trips"].to_numpy(float),
            zorder=9
        )

    selected_refill_rows = np.unique(selected["Best Refill Row"].to_numpy(np.int32))
    supporting_refills = scenario.refills.loc[selected_refill_rows].to_crs(PROJECTED_CRS)
    supporting_refills.plot(
        ax=ax, color=REFILL_COLOR, edgecolor="white", linewidth=0.55,
        marker="s", markersize=28, zorder=8
    )
    base_rows = supporting_refills["Supporting Base Row"].astype(int).unique()
    supporting_bases = scenario.dispatch_bases.iloc[base_rows].to_crs(PROJECTED_CRS)
    supporting_bases.plot(
        ax=ax, color=BASE_COLOR, edgecolor="white", linewidth=0.45,
        marker="^", markersize=28, zorder=8
    )

    total_demand_liters = float(
        scenario.units["Estimated Water Demand (L/day)"].sum()
    )
    delivered_share = result.delivery_liters / total_demand_liters
    ax.text(
        0.02,
        0.035,
        (
            f"{scenario.label}\n"
            f"Delivered: {result.delivery_liters / 1000:,.1f}/"
            f"{total_demand_liters / 1000:,.1f} m³/day ({delivered_share:.1%})\n"
            f"Fleet/trips: {result.fleet_used}/{fleet_size} tankers; "
            f"{result.trips_used}/{fleet_size * scenario.trip_limit} trips\n"
            f"Selected sites: {len(selected)} "
            f"({int(selected['Temporary Site'].sum())} temporary)"
        ),
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.7,
        linespacing=1.2,
        bbox={
            "boxstyle": "round,pad=0.35", "facecolor": "white",
            "edgecolor": "#808080", "linewidth": 0.5, "alpha": 0.94,
        },
        zorder=20,
    )
    style_map(ax, projected_bounds, geographic_bounds)


def add_legend_panel(ax: plt.Axes) -> None:
    """Use the fourth 2x2 cell as one integrated, mobile-readable legend."""
    ax.set_axis_off()
    ax.add_patch(
        FancyBboxPatch(
            (0.025, 0.035),
            0.95,
            0.93,
            transform=ax.transAxes,
            boxstyle="round,pad=0.012",
            facecolor="#fbfbfa",
            edgecolor="#7f878d",
            linewidth=0.8,
            zorder=0,
        )
    )
    ax.text(
        0.065,
        0.925,
        "Legend",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=12.5,
        fontweight="bold",
        color="#263238",
    )

    distance_handles = [
        Patch(facecolor=DISTANCE_COLORS[label], edgecolor="#7b8790", label=label)
        for label in DISTANCE_LABELS
    ]
    distance_legend = ax.legend(
        handles=distance_handles,
        title="Distance to nearest eligible point",
        loc="upper left",
        bbox_to_anchor=(0.055, 0.84),
        ncol=2,
        frameon=False,
        fontsize=8.8,
        title_fontsize=9.5,
        labelspacing=0.8,
        columnspacing=1.5,
        handlelength=1.8,
        borderaxespad=0,
    )
    distance_legend._legend_box.align = "left"
    ax.add_artist(distance_legend)

    logistics_handles = [
        Patch(
            facecolor=FLEET_GAP_COLOR,
            edgecolor="#b56a21",
            label="Within panel catchment but unserved (fleet gap)",
        ),
        Line2D(
            [0], [0], marker="o", color="none", markerfacecolor=SITE_COLOR,
            markeredgecolor="white", markersize=7,
            label="Selected announced point (size = trips)",
        ),
        Line2D(
            [0], [0], marker="*", color="none", markerfacecolor=TEMP_COLOR,
            markeredgecolor="white", markersize=10,
            label="Selected temporary point (size = trips)",
        ),
        Line2D(
            [0], [0], marker="s", color="none", markerfacecolor=REFILL_COLOR,
            markeredgecolor="white", markersize=7,
            label="Selected historical refill candidate",
        ),
        Line2D(
            [0], [0], marker="^", color="none", markerfacecolor=BASE_COLOR,
            markeredgecolor="white", markersize=7,
            label="Supporting dispatch base",
        ),
    ]
    logistics_legend = ax.legend(
        handles=logistics_handles,
        title="Allocation and logistics",
        loc="lower left",
        bbox_to_anchor=(0.055, 0.20),
        ncol=1,
        frameon=False,
        fontsize=8.8,
        title_fontsize=9.5,
        labelspacing=0.72,
        handletextpad=0.8,
        borderaxespad=0,
    )
    logistics_legend._legend_box.align = "left"
    ax.text(
        0.065,
        0.60,
        "Allocation catchment: 500 / 1,000 / 2,000 m by panel",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.3,
        color="#374151",
    )
    ax.text(
        0.065,
        0.565,
        "2,000 m is an extended diagnostic, not a walking standard.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.7,
        color="#5f6b76",
    )


def focused_plot_bounds(
    scenarios: list[tuple[ScenarioInputs, AllocationResult]],
) -> tuple[tuple[float, float, float, float], tuple[float, float, float, float]]:
    """Bound maps to positive-demand units and facilities used by the solutions."""
    geometry_parts: list[gpd.GeoSeries] = []
    for scenario, result in scenarios:
        geometry_parts.append(scenario.units.geometry)
        geometry_parts.append(result.selected_sites.geometry)
        selected = result.selected_sites
        refill_rows = np.unique(selected["Best Refill Row"].to_numpy(np.int32))
        supporting_refills = scenario.refills.loc[refill_rows]
        geometry_parts.append(supporting_refills.geometry)
        base_rows = supporting_refills["Supporting Base Row"].astype(int).unique()
        geometry_parts.append(scenario.dispatch_bases.iloc[base_rows].geometry)

    focus = gpd.GeoDataFrame(
        geometry=pd.concat(geometry_parts, ignore_index=True),
        crs=scenarios[0][0].units.crs,
    ).to_crs(PROJECTED_CRS)
    min_x, min_y, max_x, max_y = (float(value) for value in focus.total_bounds)
    padding_m = 3_000.0
    projected_bounds = (
        min_x - padding_m,
        min_y - padding_m,
        max_x + padding_m,
        max_y + padding_m,
    )
    geographic_bounds = tuple(
        float(value)
        for value in gpd.GeoSeries(
            [box(*projected_bounds)], crs=PROJECTED_CRS
        ).to_crs(4326).total_bounds
    )
    return projected_bounds, geographic_bounds


def main() -> None:
    parameters = pd.read_parquet(PARAMETERS)
    fleet_size = int(parameter_values(parameters, "Fleet Size")["central"])
    if fleet_size != 10:
        raise ValueError("Primary fleet size is no longer 10 vehicles")
    nodes = gpd.read_parquet(ROAD_NODES, columns=["Network Node ID", "Geometry"])
    edges = pd.read_parquet(
        ROAD_EDGES,
        columns=[
            "Road Edge ID", "From Node ID", "To Node ID", "Road Length (m)",
            "Baseline Edge Travel Time (min)", "Road Available",
            "Network Analysis Eligible",
        ],
    )
    demand = gpd.read_parquet(
        MESH_DEMAND,
        columns=[
            "Mesh Code", "Geometry", "Outage Population Scenario", "Demand Scenario",
            "Estimated Outage Population", "Estimated Water Demand (L/day)",
        ],
    )
    access = pd.read_parquet(MESH_ACCESS)
    water = gpd.read_parquet(WATER_POINTS)
    staging = gpd.read_parquet(STAGING)
    older_weight = older_priority_weights()
    scenario_specs = [
        ("500 m: Access-constrained", 500.0),
        ("1,000 m: Transition", 1_000.0),
        ("2,000 m: Capacity-constrained", 2_000.0),
    ]
    scenarios: list[tuple[ScenarioInputs, AllocationResult]] = []
    reproducibility_audit: list[dict[str, object]] = []
    for label, access_distance_m in scenario_specs:
        scenario = prepare_scenario(
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
        result = solve_allocation(scenario, fleet_size)
        repeat_result = solve_allocation(scenario, fleet_size)
        validate_solution(scenario, result, fleet_size)
        validate_solution(scenario, repeat_result, fleet_size)
        first_signature = allocation_signature(scenario, result)
        repeat_signature = allocation_signature(scenario, repeat_result)
        substantive_keys = [
            "delivery_liters", "fleet_used", "trips_used", "temporary_sites"
        ]
        substantive_agreement = all(
            first_signature[key] == repeat_signature[key]
            for key in substantive_keys
        )
        if not substantive_agreement:
            raise RuntimeError(
                f"Independent reruns disagree on substantive objectives for {label}"
            )
        exact_agreement = first_signature == repeat_signature
        reproducibility_audit.append(
            {
                "scenario": label,
                "thread_convention": "single thread",
                "substantive_objective_agreement": substantive_agreement,
                "selected_site_agreement": (
                    first_signature["selected_site_ids"]
                    == repeat_signature["selected_site_ids"]
                ),
                "exact_solution_agreement": exact_agreement,
                "interpretation": (
                    "reproducible configuration"
                    if exact_agreement
                    else "substantively equivalent alternative configurations"
                ),
                "first_signature": first_signature,
                "repeat_signature": repeat_signature,
                "repeat_stages": list(repeat_result.solver_audit),
            }
        )
        scenarios.append((scenario, result))

    municipalities = gpd.read_parquet(MUNICIPALITIES)
    affected_municipalities = municipalities.loc[
        municipalities["Reporting Municipality Name"].isin(["八代市", "宇城市", "氷川町"])
    ].copy()
    if len(affected_municipalities) != 3:
        raise ValueError("Expected the three positive-outage municipalities")
    municipalities = municipalities.to_crs(PROJECTED_CRS)

    sns.set_theme(style="white", context="paper")
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 9.2), constrained_layout=True)
    map_axes = [axes[0, 0], axes[0, 1], axes[1, 0]]
    key_ax = axes[1, 1]
    projected_bounds, geographic_bounds = focused_plot_bounds(scenarios)
    for scenario, result in scenarios:
        validate_solution(scenario, result, fleet_size)
    for label, ax, (scenario, result) in zip(
        "abc", map_axes, scenarios, strict=True
    ):
        add_panel(
            ax,
            scenario,
            result,
            fleet_size,
            municipalities,
            projected_bounds,
            geographic_bounds,
        )
        ax.text(
            -0.03, 1.02, label, transform=ax.transAxes, fontsize=12,
            fontweight="bold", va="top", ha="left"
        )
    add_legend_panel(key_ax)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    solver_audit = {
        "runs": [
            {
                "scenario": scenario.label,
                "fleet_size": fleet_size,
                "delivery_liters": result.delivery_liters,
                "fleet_used": result.fleet_used,
                "trips_used": result.trips_used,
                "stages": list(result.solver_audit),
            }
            for scenario, result in scenarios
        ],
        "reproducibility": reproducibility_audit,
    }
    SOLVER_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SOLVER_AUDIT_PATH.write_text(
        json.dumps(solver_audit, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    for scenario, result in scenarios:
        print(
            f"{scenario.label}: delivered={result.delivery_liters / 1000:,.3f} m3/day; "
            f"fleet used={result.fleet_used}; trips={result.trips_used}; "
            f"selected sites={len(result.selected_sites)}; "
            f"temporary={int(result.selected_sites['Temporary Site'].sum())}; "
            f"closed edges={scenario.closed_edge_count}"
        )
    for audit in reproducibility_audit:
        print(
            f"{audit['scenario']} rerun: {audit['interpretation']}; "
            f"selected-site agreement={audit['selected_site_agreement']}; "
            f"exact agreement={audit['exact_solution_agreement']}"
        )
    print(f"Saved: {OUTPUT_PATH.relative_to(ROOT)}")
    print(f"Saved audit: {SOLVER_AUDIT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
