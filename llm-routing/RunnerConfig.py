"""
Experiment Runner config. Runs on the laptop and drives the testbed over SSH
(see testbed.py): the testbed only runs the Ollama servers and run_queries.py.

  python experiment-runner/experiment-runner/ llm-routing/RunnerConfig.py
"""

import os
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
import config
import testbed

# Optional settings for additional experiments; the defaults are the main experiment.
EXPERIMENT_NAME = os.environ.get("EXPERIMENT_NAME", "llm_routing")
QUESTIONS = os.environ.get("QUESTIONS", "questions.jsonl")  # a file in llm-routing/
REPETITIONS = int(os.environ.get("REPETITIONS", "30"))
COOLDOWN_S = int(os.environ.get("COOLDOWN_S", "60"))

# Files the testbed needs, relative to the repository root; copied at the start of the experiment.
TESTBED_FILES = [
    "llm-routing/config.py",
    "llm-routing/ollama_server.py",
    "llm-routing/answers.py",
    "llm-routing/run_queries.py",
    "llm-routing/questions.jsonl",
    "llm-routing/testbed-requirements.txt",
    # The saved router refers to router.features.question_features.
    "llm-routing/router/__init__.py",
    "llm-routing/router/features.py",
    "data/router_model/router.joblib",
]
if QUESTIONS != "questions.jsonl":
    TESTBED_FILES.append(f"llm-routing/{QUESTIONS}")
PYTHON = config.TESTBED_PYTHON


class RunnerConfig:
    name = EXPERIMENT_NAME
    results_output_path = config.REPO_ROOT / "data" / "experiments"
    operation_type = OperationType.AUTO
    time_between_runs_in_ms = COOLDOWN_S * 1000
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
            repetitions=REPETITIONS,
            shuffle=True,
            data_columns=["cpu_energy_j", "gpu_energy_j", "runtime_s",
                          "gpu0_util_pct", "gpu1_util_pct", "ram_peak_mib", "vram_peak_mib",
                          "correct", "sent_to_large", "tokens", "latency_mean_s", "latency_p95_s"])
        return self.run_table_model

    def before_experiment(self):
        testbed.copy_to(TESTBED_FILES)
        # Set up the testbed's Python environment (no-op if done), then warm up the machine.
        testbed.run("python3", "-m", "venv", ".venv")
        testbed.run(PYTHON, "-m", "pip", "install", "--quiet", "-r", "testbed-requirements.txt")
        testbed.run(PYTHON, "ollama_server.py", "warmup")

    def start_run(self, context):
        testbed.run(PYTHON, "ollama_server.py", "start", context.execute_run["strategy"])

    def interact(self, context):
        run_dir = self.testbed_run_dir(context)
        testbed.run("mkdir", "-p", run_dir)
        testbed.run("energibridge", "--gpu", "-o", f"{run_dir}/energibridge.csv", "--",
                    PYTHON, "run_queries.py",
                    context.execute_run["strategy"], f"{run_dir}/queries.csv", QUESTIONS)

    def stop_run(self, context):
        testbed.run(PYTHON, "ollama_server.py", "stop")

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
