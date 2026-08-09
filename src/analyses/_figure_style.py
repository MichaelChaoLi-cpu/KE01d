"""Shared visual system for KE01d research figures."""
from __future__ import annotations

import matplotlib.pyplot as plt
import seaborn as sns


# High-contrast, colorblind-friendly palette inherited from the allocation map.
BLUE = "#0072B2"
GREEN = "#009E73"
YELLOW = "#F0E442"
VERMILLION = "#D55E00"
MAGENTA = "#CC79A7"
BLACK = "#111827"
PURPLE = "#7B2CBF"

LIGHT_GREY = "#ECEFF1"
MID_GREY = "#8D99AE"
GRID_GREY = "#D7DDE2"
BORDER_GREY = "#374151"
BOUNDARY_GREY = "#4D4D4D"
ANNOTATION_GREY = "#808080"
PANEL_FILL = "#FBFBFA"

SCENARIO_COLORS = {
    "Baseline roads": BLUE,
    "No modeled road closures": BLUE,
    "Matched restrictions closed": VERMILLION,
    "Road-restriction stress test": VERMILLION,
    "Worst single-point failure": MAGENTA,
    "Worst single announced-point failure": MAGENTA,
}

DISTANCE_COLORS = {
    "<=250 m": BLUE,
    "250-500 m": GREEN,
    "500-1,000 m": YELLOW,
    "1,000-2,000 m": VERMILLION,
    "2,000-5,000 m": MAGENTA,
    ">5,000 m or unreachable": LIGHT_GREY,
}


def set_theme() -> None:
    """Apply the shared white-background publication theme."""
    sns.set_theme(style="white", context="paper")
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "axes.edgecolor": BORDER_GREY,
            "axes.linewidth": 0.85,
            "axes.labelcolor": BLACK,
            "xtick.color": BORDER_GREY,
            "ytick.color": BORDER_GREY,
            "text.color": BLACK,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "legend.framealpha": 0.96,
            "legend.edgecolor": ANNOTATION_GREY,
        }
    )


def panel_label(ax: plt.Axes, label: str, x: float = -0.03, y: float = 1.02) -> None:
    """Place a consistent lowercase panel label outside the upper-left frame."""
    ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        fontsize=12,
        fontweight="bold",
        va="top",
        ha="left",
        color=BLACK,
    )


def annotation_box(
    ax: plt.Axes,
    text: str,
    *,
    x: float = 0.02,
    y: float = 0.03,
    ha: str = "left",
    va: str = "bottom",
    fontsize: float = 8.0,
    zorder: int = 9,
) -> None:
    """Add the compact lower-left annotation used by the allocation map."""
    ax.text(
        x,
        y,
        text,
        transform=ax.transAxes,
        ha=ha,
        va=va,
        fontsize=fontsize,
        linespacing=1.2,
        bbox={
            "boxstyle": "round,pad=0.35",
            "facecolor": "white",
            "edgecolor": ANNOTATION_GREY,
            "linewidth": 0.5,
            "alpha": 0.94,
        },
        zorder=zorder,
    )


def style_cartesian_axis(ax: plt.Axes) -> None:
    """Apply the common grid and complete frame to a non-map panel."""
    ax.grid(True, color=GRID_GREY, linewidth=0.65)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(BORDER_GREY)
        spine.set_linewidth(0.85)
