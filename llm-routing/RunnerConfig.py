import subprocess
import sys
from pathlib import Path

import pandas as pd

from EventManager.Models.RunnerEvents import RunnerEvents
from EventManager.EventSubscriptionController import EventSubscriptionController
from ConfigValidator.Config.Models.RunTableModel import RunTableModel
from ConfigValidator.Config.Models.FactorModel import FactorModel
from ConfigValidator.Config.Models.OperationType import OperationType

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
import ollama_server

class RunnerConfig:
    name = "llm_routing"
    results_output_path = HERE / "experiments"
    operation_type = OperationType.AUTO
    time_between_runs_in_ms = 60_000
    experiment_path = None

    def __init__(self):
        EventSubscriptionController.subscribe_to_multiple_events([
            (RunnerEvents.START_RUN,         self.start_run),
            (RunnerEvents.INTERACT,          self.interact),
            (RunnerEvents.STOP_RUN,          self.stop_run),
            (RunnerEvents.POPULATE_RUN_DATA, self.populate_run_data),
        ])

    def create_run_table_model(self):
        self.run_table_model = RunTableModel(
            factors=[FactorModel("strategy", ["S", "L", "R"])],
            repetitions=30,
            shuffle=True,
            data_columns=["cpu_energy_j", "gpu_energy_j", "runtime_s",
                          "gpu0_util_pct", "gpu1_util_pct", "ram_peak_mib", "vram_peak_mib",
                          "correct", "sent_to_large", "tokens", "latency_mean_s", "latency_p95_s"])
        return self.run_table_model

    def start_run(self, context):
        ollama_server.start_strategy(context.execute_run["strategy"])

    def interact(self, context):
        subprocess.run(["sudo", "energibridge", "--gpu", "-o", context.run_dir / "energibridge.csv", "--",
                        sys.executable, HERE / "run_queries.py",
                        context.execute_run["strategy"], context.run_dir / "queries.csv"], check=True)

    def stop_run(self, context):
        ollama_server.stop_all()

    def populate_run_data(self, context):
        eb = pd.read_csv(context.run_dir / "energibridge.csv")
        q = pd.read_csv(context.run_dir / "queries.csv")
        seconds = eb["Time"].diff().fillna(0) / 1000
        cpu_steps = eb["CPU_ENERGY (J)"].diff().fillna(0)
        return {
            "cpu_energy_j":   cpu_steps[cpu_steps >= 0].sum(),
            "gpu_energy_j":   ((eb["GPU0_POWER (mWatts)"] + eb["GPU1_POWER (mWatts)"]) / 1000 * seconds).sum(),
            "runtime_s":      seconds.sum(),
            "gpu0_util_pct":  eb["GPU0_USAGE"].mean(),
            "gpu1_util_pct":  eb["GPU1_USAGE"].mean(),
            "ram_peak_mib":   eb["USED_MEMORY"].max() / 2**20,
            "vram_peak_mib":  (eb["GPU0_MEMORY_USED"] + eb["GPU1_MEMORY_USED"]).max(),
            "correct":        q["correct"].sum(),
            "sent_to_large":  (q["model"] == "large").sum(),
            "tokens":         q["completion_tokens"].sum(),
            "latency_mean_s": q["latency_s"].mean(),
            "latency_p95_s":  q["latency_s"].quantile(0.95),
        }
