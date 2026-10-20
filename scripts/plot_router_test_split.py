"""Plot how well the experiment's router chooses models on the full GSM8K test split.

For each share of questions sent to the large model, the router sends the questions
it rates least likely to be answered by the small model. The figure compares the
resulting accuracy with choosing the model at random, and marks the router's
threshold used in the experiment. Labels come from data/labels/test_{small,large}.jsonl.
Also writes the router's predictions to data/analysis/router_test_predictions.csv,
which analysis/04_accuracy_tradeoff.R reads.

  uv run --group analysis python scripts/plot_router_test_split.py
"""

import json
import sys
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "llm-routing"))

import config  # noqa: E402

OUT = REPO_ROOT / "data" / "analysis" / "figures" / "router_test_split.png"
PREDICTIONS = REPO_ROOT / "data" / "analysis" / "router_test_predictions.csv"
GREEN, INK, SECONDARY, MUTED = "#1baf7a", "#0b0b0b", "#52514e", "#898781"


def labels(model: str) -> np.ndarray:
    rows = sorted(map(json.loads, open(REPO_ROOT / "data" / "labels" / f"test_{model}.jsonl")), key=lambda r: r["qid"])
    return np.array([r["correct"] for r in rows])


def main() -> None:
    questions = [json.loads(line)["question"] for line in open(REPO_ROOT / "data" / "dataset" / "test.jsonl")]
    small_ok, large_ok = labels("small"), labels("large")
    router = joblib.load(config.ROUTER_FILE)
    p_small = router.predict_proba(questions)[:, list(router.classes_).index(1)]
    n = len(questions)
    PREDICTIONS.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"qid": range(n), "p_small_correct": p_small, "threshold": config.ROUTER_THRESHOLD,
                  "small_correct": small_ok, "large_correct": large_ok}).to_csv(PREDICTIONS, index=False)

    order = np.argsort(p_small)  # least likely to be solved by the small model first
    share = 100 * np.arange(n + 1) / n
    routed = 100 * np.array([large_ok[order][:k].sum() + small_ok[order][k:].sum() for k in range(n + 1)]) / n
    random_choice = 100 * (small_ok.sum() + np.arange(n + 1) * (large_ok.sum() - small_ok.sum()) / n) / n

    to_large = p_small <= config.ROUTER_THRESHOLD
    point_share = 100 * to_large.mean()
    point_correct = 100 * np.where(to_large, large_ok, small_ok).mean()

    gap = point_correct - np.interp(point_share, share, random_choice)

    plt.rcParams.update({
        "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "axes.edgecolor": "#c3c2b7",
        "axes.labelcolor": SECONDARY, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": "#e1e0d9", "grid.linewidth": 0.6, "xtick.color": MUTED,
        "ytick.color": MUTED, "text.color": INK, "lines.linewidth": 2, "font.size": 10, "legend.frameon": False,
    })
    fig, ax = plt.subplots(figsize=(7.2, 5.4))

    ax.plot(share, random_choice, ":", color=MUTED, linewidth=2,
            label="random choice: same share sent to 9B, questions picked at random")
    ax.plot(share, routed, color=GREEN,
            label="router: questions it rates hardest for 2B go to 9B")
    ax.scatter([point_share], [point_correct], s=80, color=GREEN, edgecolor=INK, zorder=3)
    ax.annotate(f"threshold {config.ROUTER_THRESHOLD} (used in the experiment)\n"
                f"{point_share:.1f}% of questions go to 9B\n"
                f"accuracy {point_correct:.1f}% ({gap:+.1f} vs random)",
                (point_share, point_correct), xytext=(point_share + 4, point_correct - 13),
                fontsize=8.5, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED))
    ax.annotate(f"all questions to 2B\naccuracy {random_choice[0]:.1f}%", (0, random_choice[0]),
                xytext=(2, -26), textcoords="offset points", fontsize=8.5, color=SECONDARY)
    ax.annotate(f"all questions to 9B\naccuracy {random_choice[-1]:.1f}%", (100, random_choice[-1]),
                xytext=(-2, 8), textcoords="offset points", fontsize=8.5, color=SECONDARY, ha="right")
    ax.set_xlim(-2, 104)
    ax.set_ylim(45, 95)
    ax.set_xlabel("Questions sent to the 9B model (%)")
    ax.set_ylabel("Accuracy on all questions (%)")
    ax.legend(loc="upper left", fontsize=8.5)

    # The threshold decides how many questions go to 9B, so show it as a second x-axis on top.
    top = ax.twiny()
    top.set_xlim(-2, 104)
    thresholds = (0.3, 0.4, 0.5, config.ROUTER_THRESHOLD, 0.6, 0.7)
    top.set_xticks([100 * (p_small <= t).mean() for t in thresholds])
    top.set_xticklabels([f"{t:g}" for t in thresholds])
    top.get_xticklabels()[thresholds.index(config.ROUTER_THRESHOLD)].set_fontweight("bold")
    top.set_xlabel("Router threshold (higher threshold = more questions sent to 9B)", fontsize=9)
    top.grid(False)
    top.spines["top"].set_visible(True)

    ax.axvline(point_share, color=MUTED, linewidth=0.8, zorder=0)

    fig.suptitle("Does the router send the right questions to the 9B model?", x=0.01, ha="left",
                 fontsize=11, color=INK)
    fig.text(0.01, 0.92, f"Each point = one threshold applied to all {n} questions, then the answers are scored.",
             fontsize=8.5, color=SECONDARY)
    fig.text(0.01, 0.01, f"All {n} GSM8K test questions; correctness of both models measured on a Mac.",
             fontsize=7.5, color=MUTED)
    fig.subplots_adjust(left=0.12, right=0.97, top=0.80, bottom=0.13)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)

    print(f"questions: {n} | small correct {100 * small_ok.mean():.1f}% | large correct {100 * large_ok.mean():.1f}%")
    print(f"router AUC (small correct): {roc_auc_score(small_ok, p_small):.3f}")
    print(f"at threshold {config.ROUTER_THRESHOLD}: {point_share:.1f}% to large, {point_correct:.1f}% correct "
          f"({gap:+.1f} pp vs random choice at the same share)")
    print(f"average gain over random choice across all shares: {np.mean(routed - random_choice):+.2f} pp")
    print(f"wrote {OUT.relative_to(REPO_ROOT)} and {PREDICTIONS.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
