import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

R_COLOR = "#5BB98B"


def load_queries(data_dir: Path) -> pd.DataFrame:
    """add strategy for all question rows of the finished runs"""
    runs = pd.read_csv(data_dir / "run_table.csv").rename(columns={"__run_id": "run_id", "__done": "done"})
    runs = runs[runs.done == "DONE"]
    return pd.concat(
        pd.read_csv(data_dir / r.run_id / "queries.csv", usecols=["qid", "model", "p_small_correct", "correct"])
          .assign(strategy=r.strategy)
        for r in runs.itertuples()
    )


def per_question(q: pd.DataFrame) -> pd.DataFrame:
    """enrich with which router got it right and the P that routing to small was correct"""
    correct = q.groupby(["qid", "strategy"])["correct"].mean().unstack() >= 0.5
    p_small = q[q.strategy == "R"].groupby("qid")["p_small_correct"].first()
    return pd.DataFrame({"correct_S": correct["S"], "correct_L": correct["L"], "p_small_correct": p_small})


def router_sweep(pq: pd.DataFrame) -> pd.DataFrame:
    """P(small correct) > threshold for all possible thresholds"""
    rows = []
    for th in np.round(np.arange(0.0, 1.0001, 0.01), 2):
        small = pq.p_small_correct > th
        rows.append({"threshold": th, "sent_to_large": int((~small).sum()),
                     "correct": int(np.where(small, pq.correct_S, pq.correct_L).sum())})
    return pd.DataFrame(rows)


def oracle_curve(pq: pd.DataFrame) -> np.ndarray:
    """best possible correct count for each number of questions sent to large"""
    gain = (pq.correct_L.astype(int) - pq.correct_S.astype(int)).sort_values(ascending=False).to_numpy()
    return int(pq.correct_S.sum()) + np.concatenate([[0], np.cumsum(gain)])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=Path("data/experiments/llm_routing"))
    ap.add_argument("--out", type=Path, default=Path("data/analysis/figures"))
    ap.add_argument("--threshold", type=float, default=0.55, help="router threshold used in the experiment")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    q = load_queries(args.data)
    pq = per_question(q)
    sweep = router_sweep(pq)

    r = q[q.strategy == "R"]
    n_reps = len(r) // len(pq)
    r_large = (r.model == "large").sum() / n_reps
    r_correct = r.correct.sum() / n_reps

    k = np.arange(len(pq) + 1)
    s_c, l_c = pq.correct_S.sum(), pq.correct_L.sum()

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.plot(k, s_c + k * (l_c - s_c) / len(pq), ":", color="black", label="random choice of model (expected)")
    ax.plot(k, oracle_curve(pq), "--", color="grey", label="oracle router")
    sw = sweep.drop_duplicates("sent_to_large")
    ax.plot(sw.sent_to_large, sw.correct, "o-", ms=3, color=R_COLOR, alpha=0.7,
            label="our router at other thresholds")
    ax.scatter([r_large], [r_correct], s=90, color=R_COLOR, edgecolor="black", zorder=4,
               label=f"R in the experiment (threshold {args.threshold})")
    ax.set_xlabel("Questions sent to the large model (/100)")
    ax.set_ylabel("Correct answers (/100)")
    ax.set_title("Does the router pick the right questions?")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    out = args.out / "accuracy_vs_share_large.png"
    fig.savefig(out, dpi=150)
    print(f"R: {r_large:.0f} to large, {r_correct:.0f} correct. Wrote {out}")


if __name__ == "__main__":
    main()
