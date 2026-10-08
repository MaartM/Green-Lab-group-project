"""Shared plot style: one fixed color per strategy, thin marks, recessive axes and grid."""

import matplotlib.pyplot as plt

from experiment_data import STRATEGIES, STRATEGY_NAMES

# Categorical palette in fixed order (validated for color-vision deficiencies).
COLORS = dict(zip(STRATEGIES, ["#2a78d6", "#eb6834", "#1baf7a"]))
INK, SECONDARY, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"


def apply() -> None:
    plt.rcParams.update({
        "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
        "axes.edgecolor": AXIS, "axes.labelcolor": SECONDARY, "axes.titlecolor": INK,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
        "lines.linewidth": 2, "font.size": 10, "axes.titlesize": 11,
        "legend.frameon": False, "figure.dpi": 110,
    })


def label(strategy: str) -> str:
    return f"{strategy} ({STRATEGY_NAMES[strategy]})"
