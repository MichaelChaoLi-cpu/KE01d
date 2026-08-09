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
from matplotlib.colors import LinearSegmentedColormap, PowerNorm
from matplotlib.patches import FancyBboxPatch
from matplotlib.patches import Patch
from pyproj import Transformer
from shapely.geometry import LineString

from _figure_style import (
    ANNOTATION_GREY,
    BLACK,
    BLUE,
    BOUNDARY_GREY,
    GREEN,
    LIGHT_GREY,
    PANEL_FILL,
    YELLOW,
    annotation_box,
    panel_label,
    set_theme,
)


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
        ax=ax, color=LIGHT_GREY, edgecolor="none", rasterized=True
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
    municipalities.boundary.plot(ax=ax, color=BOUNDARY_GREY, linewidth=0.35)

    population = float(scenario.loc[known, POPULATION_COLUMN].sum())
    demand = float(scenario.loc[known, DEMAND_COLUMN].sum())
    unknown = int((~known).sum())
    annotation_box(
        ax,
        (
            f"{label}\n"
            f"Affected population: {population:,.0f}\n"
            f"Minimum demand: {demand / 1_000:,.1f} m3/day"
        ),
        fontsize=8.2,
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

    cmap = LinearSegmentedColormap.from_list(
        "ke01d_water_demand", [YELLOW, GREEN, BLUE, BLACK]
    )
    norm = PowerNorm(gamma=0.5, vmin=0, vmax=float(positive_values.max()))
    set_theme()
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 9.2), constrained_layout=True)
    map_axes = [axes[0, 0], axes[0, 1], axes[1, 0]]
    key_ax = axes[1, 1]

    summaries: list[dict[str, float | int | str]] = []
    for letter, ax, (scenario_value, display_label) in zip(
        "abc", map_axes, SCENARIOS, strict=True
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
        panel_label(ax, letter)

    key_ax.set_axis_off()
    card_ax = key_ax.inset_axes([0.19, 0.305, 0.62, 0.39])
    card_ax.set_axis_off()
    card_ax.add_patch(
        FancyBboxPatch(
            (0.02, 0.02), 0.96, 0.96,
            boxstyle="round,pad=0.006,rounding_size=0.02",
            transform=card_ax.transAxes,
            facecolor=PANEL_FILL,
            edgecolor=ANNOTATION_GREY,
            linewidth=0.8,
        )
    )
    card_ax.text(
        0.07, 0.88, "Legend", transform=card_ax.transAxes,
        fontsize=9.3, fontweight="bold", va="top", color=BLACK,
    )
    card_ax.text(
        0.07, 0.69, "Minimum emergency water demand",
        transform=card_ax.transAxes, fontsize=7.3, va="top", color=BLACK,
    )
    colorbar_ax = card_ax.inset_axes([0.07, 0.49, 0.84, 0.085])
    colorbar = fig.colorbar(
        ScalarMappable(norm=norm, cmap=cmap), cax=colorbar_ax, orientation="horizontal"
    )
    colorbar.set_label(
        "L/day per 125 m mesh (square-root scale)", fontsize=6.6, labelpad=1
    )
    colorbar.set_ticks([0, 200, 400, 600])
    colorbar.ax.tick_params(labelsize=6.5, pad=1)
    legend_handles = [
        Patch(
            facecolor="#ffffff",
            edgecolor=ANNOTATION_GREY,
            label="Zero demand (officially reported zero)",
        ),
        Patch(
            facecolor=LIGHT_GREY,
            edgecolor=ANNOTATION_GREY,
            label="Zero demand (absent from official outage listing)",
        ),
    ]
    card_ax.legend(
        handles=legend_handles,
        loc="upper left",
        bbox_to_anchor=(0.052, 0.27),
        frameon=False,
        fontsize=6.6,
        handlelength=1.5,
        handletextpad=0.55,
        labelspacing=0.3,
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    audit = pd.DataFrame(summaries)
    print(audit.to_string(index=False))
    print(f"Saved: {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
