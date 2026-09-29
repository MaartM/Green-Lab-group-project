"""
Experiment Runner config. Runs on the laptop and drives the testbed over SSH
(see testbed.py): the testbed only runs the Ollama servers and run_queries.py.

  python experiment-runner/experiment-runner/ llm-routing/RunnerConfig.py
"""

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
import testbed

# Everything the testbed needs to run the experiment, copied once per experiment.
TESTBED_FILES = [HERE / name for name in
                 ("config.py", "ollama_server.py", "run_queries.py", "questions.jsonl")]


class RunnerConfig:
    name = "llm_routing"
    results_output_path = HERE / "experiments"
    operation_type = OperationType.AUTO
    time_between_runs_in_ms = 60_000
    experiment_path = None

    def __init__(self):
        EventSubscriptionController.subscribe_to_multiple_events([
            (RunnerEvents.BEFORE_EXPERIMENT, self.before_experiment),
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

    def before_experiment(self):
        testbed.copy_to(TESTBED_FILES)

    def start_run(self, context):
        testbed.run("python3", "ollama_server.py", "start", context.execute_run["strategy"])

    def interact(self, context):
        run_dir = self.testbed_run_dir(context)
        testbed.run("mkdir", "-p", run_dir)
        testbed.run("energibridge", "--gpu", "-o", f"{run_dir}/energibridge.csv", "--",
                    "python3", "run_queries.py",
                    context.execute_run["strategy"], f"{run_dir}/queries.csv")

    def stop_run(self, context):
        testbed.run("python3", "ollama_server.py", "stop")

    def populate_run_data(self, context):
        testbed.copy_from(self.testbed_run_dir(context), context.run_dir)
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

    def testbed_run_dir(self, context):
        """Where this run's output files are written on the testbed."""
        return f"runs/{self.name}/{context.run_dir.name}"
