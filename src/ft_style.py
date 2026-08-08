"""Financial Times figure style for Part B exhibits.

Ported from the verified z5594806_projectA/src/ft_style.py, unchanged. Self-
contained copy of the course FT style (palette + rcParams + title block) so this
project reproduces on a clean checkout without importing from anywhere else.
Style code only - no portfolio maths, no data logic.

Usage:
    from src.ft_style import apply_ft_style, ft_header, save_ft
    import matplotlib.pyplot as plt

    apply_ft_style()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(...)
    ft_header(fig, "The Min-CVaR fund loses less on the worst joint-crash days",
              "Fund return on flagged co-crash days vs normal days, 2020-2023",
              "Source: project data | daily adjClose returns")
    save_ft(fig, "results/figures/example.png")
"""
from __future__ import annotations

import matplotlib.pyplot as plt

# Financial Times palette (matches the course figures).
FT_CREAM = "#FDF1E6"   # figure / axes background
FT_MAROON = "#990F3D"  # primary series
FT_BLUE = "#0F5499"    # secondary series
FT_TEAL = "#2F7F73"    # third accent
FT_GREY = "#6B625C"    # subtitle / source / muted text
FT_AXIS = "#66605C"    # axis + zero line
FT_GRID = "#E2D8CF"    # gridlines
FT_TITLE = "#262A33"   # title text


def apply_ft_style() -> None:
    """Set rcParams so the next figure follows the clean FT-style look.

    figsize is chosen per-figure in the calling code (10x6 default; up to 10x7 /
    9x8 for dense plots), not here.
    """
    plt.rcParams.update({
        "figure.facecolor": FT_CREAM,
        "axes.facecolor": FT_CREAM,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.edgecolor": FT_AXIS,
        "axes.grid": True,
        "grid.color": FT_GRID,
        "axes.axisbelow": True,
        "font.family": "DejaVu Sans",
        "font.size": 12,
    })


def ft_header(fig, title: str, subtitle: str, source: str) -> None:
    """Write the FT-style title / subtitle / source block onto a figure.

    The title states the conclusion (not a label). Call after plotting.
    """
    fig.text(0.012, 0.96, title, fontsize=15, fontweight="bold", color=FT_TITLE)
    fig.text(0.012, 0.91, subtitle, fontsize=11, color=FT_GREY)
    fig.text(0.012, 0.01, source, fontsize=8, color=FT_GREY)
    fig.subplots_adjust(top=0.86, bottom=0.12)


def save_ft(fig, path: str, dpi: int = 150) -> None:
    """Save a figure at the course-standard dpi on the cream background."""
    fig.savefig(path, dpi=dpi, facecolor=fig.get_facecolor())
