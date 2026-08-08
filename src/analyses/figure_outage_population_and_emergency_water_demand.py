#!/usr/bin/env python3
"""Outage Population and Emergency Water Demand.

Plan: Map affected-population estimates and minimum emergency-water demand
under the lower, central, and upper outage-population planning bounds.
Framework: AnaSOP Sections 5-7 demand equations and the resident-demand
construction workflow. Municipalities absent from the exhaustive official
outage listing are coded as assumed zero; unmatched geography remains missing.
"""
from __future__ import annotations

import math
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.cm import ScalarMappable
from matplotlib.colors import PowerNorm
from matplotlib.patches import Patch
from pyproj import Transformer
from shapely.geometry import LineString


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = (
    ROOT
    / "data/processed/population_mesh_outage_demand_scenarios_preprocessed.parquet"
)
MUNICIPALITY_PATH = (
    ROOT / "data/processed/kumamoto_reporting_municipalities_preprocessed.parquet"
)
OUTPUT_PATH = (
    ROOT
    / "data/results/figures/Figure_outage_population_and_emergency_water_demand.png"
)
PROJECTED_CRS = 6670
GEOGRAPHIC_CRS = 6668

DEMAND_COLUMN = "Estimated Water Demand (L/day)"
POPULATION_COLUMN = "Estimated Outage Population"
SCENARIO_COLUMN = "Outage Population Scenario"
SCENARIOS = [
    ("lower_one_person_per_household", "Lower bound"),
    ("proportional_central", "Central estimate"),
    ("upper_p90_household_size", "Upper bound"),
]


def load_inputs() -> tuple[
    gpd.GeoDataFrame,
    gpd.GeoDataFrame,
    tuple[float, float, float, float],
]:
    """Load the minimum-demand mesh scenarios and reporting boundaries."""
    meshes = gpd.read_parquet(
        SCENARIO_PATH,
        columns=[
            "Geometry",
            SCENARIO_COLUMN,
            "Demand Scenario",
            "Outage Observation Status",
            POPULATION_COLUMN,
            DEMAND_COLUMN,
        ],
    )
    meshes = meshes.loc[meshes["Demand Scenario"].eq("minimum")].copy()
    municipalities = gpd.read_parquet(
        MUNICIPALITY_PATH,
        columns=["Geometry", "Reporting Municipality Name"],
    )
    if municipalities.crs != meshes.crs:
        municipalities = municipalities.to_crs(meshes.crs)
    geographic_bounds = tuple(float(value) for value in municipalities.total_bounds)
    return (
        meshes.to_crs(PROJECTED_CRS),
        municipalities.to_crs(PROJECTED_CRS),
        geographic_bounds,
    )


def graticule_values(lower: float, upper: float, step: float) -> list[float]:
    """Return stable graticule values within a geographic extent."""
    start = math.ceil((lower - 1e-9) / step) * step
    stop = math.floor((upper + 1e-9) / step) * step
    count = int(round((stop - start) / step)) + 1
    return [round(start + index * step, 8) for index in range(max(0, count))]


def add_graticule(
    ax: plt.Axes,
    geographic_bounds: tuple[float, float, float, float],
    step: float = 0.25,
) -> None:
    """Draw KE01c-style longitude and latitude graticules on projected axes."""
    lon_min, lat_min, lon_max, lat_max = geographic_bounds
    longitudes = graticule_values(lon_min, lon_max, step)
    latitudes = graticule_values(lat_min, lat_max, step)
    samples = 160
    lines: list[LineString] = []
    for longitude in longitudes:
        lines.append(
            LineString(
                zip(
                    np.full(samples, longitude),
                    np.linspace(lat_min - step, lat_max + step, samples),
                    strict=True,
                )
            )
        )
    for latitude in latitudes:
        lines.append(
            LineString(
                zip(
                    np.linspace(lon_min - step, lon_max + step, samples),
                    np.full(samples, latitude),
                    strict=True,
                )
            )
        )
    gpd.GeoSeries(lines, crs=GEOGRAPHIC_CRS).to_crs(PROJECTED_CRS).plot(
        ax=ax,
        color="#7d8992",
        linewidth=0.42,
        linestyle=(0, (2.5, 3.5)),
        alpha=0.48,
        zorder=3,
    )

    transformer = Transformer.from_crs(
        GEOGRAPHIC_CRS, PROJECTED_CRS, always_xy=True
    )
    centre_latitude = (lat_min + lat_max) / 2
    centre_longitude = (lon_min + lon_max) / 2
    label_style = {"fontsize": 7.0, "color": "#3f4a52", "clip_on": False}
    for longitude in longitudes:
        x_position, _ = transformer.transform(longitude, centre_latitude)
        ax.text(
            x_position,
            -0.014,
            f"{longitude:.2f}°E",
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            **label_style,
        )
    for latitude in latitudes:
        _, y_position = transformer.transform(centre_longitude, latitude)
        ax.text(
            -0.022,
            y_position,
            f"{latitude:.2f}°N",
            transform=ax.get_yaxis_transform(),
            ha="right",
            va="center",
            **label_style,
        )
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("#303a40")
        spine.set_linewidth(0.85)
        spine.set_zorder(10)


def style_map(
    ax: plt.Axes,
    projected_bounds: tuple[float, float, float, float],
    geographic_bounds: tuple[float, float, float, float],
) -> None:
    """Apply a shared extent, geographic grid, and visible map frame."""
    min_x, min_y, max_x, max_y = projected_bounds
    margin_x = (max_x - min_x) * 0.018
    margin_y = (max_y - min_y) * 0.018
    ax.set_xlim(min_x - margin_x, max_x + margin_x)
    ax.set_ylim(min_y - margin_y, max_y + margin_y)
    ax.set_aspect("equal")
    add_graticule(ax, geographic_bounds)


def add_panel(
    ax: plt.Axes,
    scenario: gpd.GeoDataFrame,
    municipalities: gpd.GeoDataFrame,
    label: str,
    norm: PowerNorm,
    cmap: str,
    projected_bounds: tuple[float, float, float, float],
    geographic_bounds: tuple[float, float, float, float],
) -> dict[str, float | int | str]:
    """Draw one scenario map and return its audit summary."""
    known = scenario[DEMAND_COLUMN].notna()
    zero = known & scenario[DEMAND_COLUMN].eq(0)
    positive = known & scenario[DEMAND_COLUMN].gt(0)
    reported_zero = zero & scenario["Outage Observation Status"].eq("reported_zero")
    assumed_zero = zero & scenario["Outage Observation Status"].eq(
        "assumed_zero_no_official_outage_listing"
    )

    scenario.loc[assumed_zero].plot(
        ax=ax, color="#eeeeee", edgecolor="none", rasterized=True
    )
    scenario.loc[reported_zero].plot(
        ax=ax, color="#ffffff", edgecolor="none", rasterized=True
    )
    scenario.loc[positive].plot(
        ax=ax,
        column=DEMAND_COLUMN,
        cmap=cmap,
        norm=norm,
        edgecolor="none",
        rasterized=True,
    )
    municipalities.boundary.plot(ax=ax, color="#4d4d4d", linewidth=0.35)

    population = float(scenario.loc[known, POPULATION_COLUMN].sum())
    demand = float(scenario.loc[known, DEMAND_COLUMN].sum())
    unknown = int((~known).sum())
    ax.text(
        0.02,
        0.98,
        (
            f"{label}\n"
            f"Affected population: {population:,.0f}\n"
            f"Minimum demand: {demand / 1_000:,.1f} m3/day"
        ),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        linespacing=1.25,
        bbox={
            "boxstyle": "round,pad=0.35",
            "facecolor": "white",
            "edgecolor": "#808080",
            "linewidth": 0.5,
            "alpha": 0.92,
        },
    )
    style_map(ax, projected_bounds, geographic_bounds)
    return {
        "scenario": label,
        "affected_population": population,
        "minimum_demand_l_day": demand,
        "known_meshes": int(known.sum()),
        "positive_meshes": int(positive.sum()),
        "unknown_meshes": unknown,
    }


def main() -> None:
    meshes, municipalities, geographic_bounds = load_inputs()
    projected_bounds = tuple(float(value) for value in municipalities.total_bounds)
    positive_values = meshes.loc[meshes[DEMAND_COLUMN].gt(0), DEMAND_COLUMN]
    if positive_values.empty:
        raise ValueError("No positive minimum-demand values are available to map.")

    cmap = "YlGnBu"
    norm = PowerNorm(gamma=0.5, vmin=0, vmax=float(positive_values.max()))
    sns.set_theme(style="white", context="paper")
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 6.2), constrained_layout=True)

    summaries: list[dict[str, float | int | str]] = []
    for panel_label, ax, (scenario_value, display_label) in zip(
        "abc", axes, SCENARIOS, strict=True
    ):
        scenario = meshes.loc[meshes[SCENARIO_COLUMN].eq(scenario_value)]
        if scenario.empty:
            raise ValueError(f"Missing planned scenario: {scenario_value}")
        summaries.append(
            add_panel(
                ax,
                scenario,
                municipalities,
                display_label,
                norm,
                cmap,
                projected_bounds,
                geographic_bounds,
            )
        )
        ax.text(
            -0.03,
            1.02,
            panel_label,
            transform=ax.transAxes,
            fontsize=12,
            fontweight="bold",
            va="top",
            ha="left",
        )

    colorbar = fig.colorbar(
        ScalarMappable(norm=norm, cmap=cmap),
        ax=axes,
        orientation="horizontal",
        fraction=0.04,
        pad=0.025,
        aspect=45,
    )
    colorbar.set_label(
        "Minimum emergency water demand (L/day per 125 m mesh; square-root color scale)"
    )
    legend_handles = [
        Patch(
            facecolor="#ffffff",
            edgecolor="#808080",
            label="Zero demand (officially reported zero)",
        ),
        Patch(
            facecolor="#eeeeee",
            edgecolor="#808080",
            label="Zero demand (absent from official outage listing)",
        ),
    ]
    axes[0].legend(
        handles=legend_handles,
        loc="lower left",
        bbox_to_anchor=(0.01, 0.01),
        frameon=True,
        framealpha=0.92,
        edgecolor="#808080",
        fontsize=8,
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    audit = pd.DataFrame(summaries)
    print(audit.to_string(index=False))
    print(f"Saved: {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
