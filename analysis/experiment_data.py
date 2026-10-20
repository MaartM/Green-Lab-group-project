"""
Load the experiment's raw data into one row per run, shared by all analysis notebooks.

Everything is recomputed from the raw per-run files (energibridge.csv and
queries.csv), not taken from Experiment Runner's run_table.csv, so the
analysis follows the definitions of report Section 5.3 exactly.
"""

from pathlib import Path

import numpy as np
import pandas as pd

EXPERIMENT_DIR = Path(__file__).resolve().parents[1] / "data" / "experiments" / "llm_routing_500"
STRATEGIES = ["S", "L", "R"]
STRATEGY_NAMES = {"S": "small-only", "L": "large-only", "R": "routing"}

# Run-level dependent variables (report Table 5): column -> label with unit.
RUN_VARIABLES = {
    "energy_j": "Total energy E (J)",
    "energy_per_query_j": "Energy per query E/N (J/query)",
    "energy_per_token_j": "Energy per output token E/K (J/token)",
    "efficiency_correct_per_kj": "Energy efficiency η = C/E (correct per kJ)",
    "time_s": "Total inference time T (s)",
    "latency_mean_s": "Mean query latency (s)",
    "latency_p95_s": "95th-percentile query latency (s)",
    "gpu0_util_pct": "Mean utilization GPU 0 (%)",
    "gpu1_util_pct": "Mean utilization GPU 1 (%)",
    "host_memory_peak_mib": "Peak host memory (MiB)",
    "gpu_memory_peak_mib": "Peak GPU memory, both GPUs (MiB)",
}


def run_ids() -> list[str]:
    return sorted(path.name for path in EXPERIMENT_DIR.glob("run_*_repetition_*"))


# EnergiBridge columns the analysis uses (the files also hold per-core CPU columns).
SAMPLE_COLUMNS = ["Time", "CPU_ENERGY (J)", "USED_MEMORY"] + [
    f"GPU{gpu}_{field}" for gpu in (0, 1)
    for field in ("POWER (mWatts)", "USAGE", "MEMORY_USED", "TEMPERATURE")]


def load_samples(run_id: str) -> pd.DataFrame:
    """EnergiBridge samples of one run, with time in seconds since its first sample."""
    samples = pd.read_csv(EXPERIMENT_DIR / run_id / "energibridge.csv", usecols=SAMPLE_COLUMNS)
    return samples.assign(t_s=(samples["Time"] - samples["Time"].iloc[0]) / 1000)


def load_queries(run_id: str) -> pd.DataFrame:
    return pd.read_csv(EXPERIMENT_DIR / run_id / "queries.csv")


def strategy_of(run_id: str) -> str:
    """Experiment Runner numbers the treatments in run table order: run_0 = S, run_1 = L, run_2 = R."""
    return STRATEGIES[int(run_id.split("_")[1])]


def energy(samples: pd.DataFrame) -> dict:
    """CPU and per-GPU energy in J, as in report Section 5.3.

    CPU: sum of the positive increments of the cumulative RAPL counter.
    GPU g: sum over samples of (time since previous sample) x (power at this sample).
    """
    cpu_steps = samples["CPU_ENERGY (J)"].diff().iloc[1:]
    dt_s = samples["Time"].diff().iloc[1:] / 1000
    result = {"cpu_energy_j": cpu_steps.clip(lower=0).sum()}
    for gpu in (0, 1):
        power_w = samples[f"GPU{gpu}_POWER (mWatts)"].iloc[1:] / 1000
        result[f"gpu{gpu}_energy_j"] = (dt_s * power_w).sum()
    return result


def summarize_run(run_id: str) -> dict:
    samples, queries = load_samples(run_id), load_queries(run_id)
    row = {"run_id": run_id, "strategy": strategy_of(run_id),
           "repetition": int(run_id.rsplit("_", 1)[1]),
           "start": pd.to_datetime(samples["Time"].iloc[0], unit="ms"),
           **energy(samples)}
    row["energy_j"] = row["cpu_energy_j"] + row["gpu0_energy_j"] + row["gpu1_energy_j"]

    n, correct, tokens = len(queries), int(queries["correct"].sum()), int(queries["completion_tokens"].sum())
    row.update(
        n_queries=n, n_correct=correct, n_tokens=tokens,
        n_to_large=int((queries["model"] == "large").sum()),
        accuracy_pct=100 * correct / n,
        energy_per_query_j=row["energy_j"] / n,
        energy_per_token_j=row["energy_j"] / tokens,
        efficiency_correct_per_kj=1000 * correct / row["energy_j"],
        time_s=samples["t_s"].iloc[-1],
        latency_mean_s=queries["latency_s"].mean(),
        latency_p95_s=queries["latency_s"].quantile(0.95),
        gpu0_util_pct=samples["GPU0_USAGE"].mean(),
        gpu1_util_pct=samples["GPU1_USAGE"].mean(),
        host_memory_peak_mib=samples["USED_MEMORY"].max() / 2**20,
        gpu_memory_peak_mib=(samples["GPU0_MEMORY_USED"] + samples["GPU1_MEMORY_USED"]).max(),
        gpu0_start_temp_c=samples["GPU0_TEMPERATURE"].iloc[0],
        gpu1_start_temp_c=samples["GPU1_TEMPERATURE"].iloc[0],
        sample_interval_median_ms=samples["Time"].diff().median(),
        sample_interval_max_ms=samples["Time"].diff().max(),
    )
    return row


def load_runs() -> pd.DataFrame:
    """One row per run, in chronological order (order = position in the experiment, from 0)."""
    runs = pd.DataFrame([summarize_run(run_id) for run_id in run_ids()])
    runs = runs.sort_values("start").reset_index(drop=True)
    runs["order"] = np.arange(len(runs))
    runs["strategy"] = pd.Categorical(runs["strategy"], STRATEGIES, ordered=True)
    return runs


def load_answers() -> pd.DataFrame:
    """Correctness per question (rows) and strategy (columns), from each strategy's first repetition.

    Generation is deterministic, so every repetition gives the same answers;
    01_data_preparation checks this before relying on it.
    """
    return pd.DataFrame({strategy: load_queries(f"run_{i}_repetition_0").set_index("qid")["correct"]
                         for i, strategy in enumerate(STRATEGIES)})
