import atexit
import posixpath
import subprocess
import sys
from pathlib import Path

import pandas as pd

from EventManager.Models.RunnerEvents import RunnerEvents
from EventManager.EventSubscriptionController import EventSubscriptionController
from ConfigValidator.Config.Models.RunTableModel import RunTableModel
from ConfigValidator.Config.Models.FactorModel import FactorModel
from ConfigValidator.Config.Models.OperationType import OperationType
from ProgressManager.Output.OutputProcedure import OutputProcedure as output

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
import config
from remote import Remote, q

CPU_ENERGY_COLUMNS = ["CPU_ENERGY (J)", "PACKAGE_ENERGY (J)"]
HOST_SIDE_FILES = ["config.py", "run_queries.py", "ollama_server.py", "ollama_client.py", "router"]
EB_COLUMNS = ["Time", "USED_MEMORY"] + [f"GPU{g}_{c}" for g in (0, 1)
                                        for c in ("POWER (mWatts)", "USAGE", "MEMORY_USED")]


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
            (RunnerEvents.AFTER_EXPERIMENT,  self.after_experiment),
        ])
        self.remote = Remote(config.REMOTE_HOST)
        self.server_pid = None
        self.remote_run_dir = None
        atexit.register(self._servers_down)

    def create_run_table_model(self):
        self.run_table_model = RunTableModel(
            factors=[FactorModel("strategy", ["S", "L", "R"])],
            repetitions=30,
            shuffle=True,
            data_columns=["cpu_energy_j", "gpu_energy_j", "runtime_s",
                          "gpu0_util_pct", "gpu1_util_pct", "ram_peak_mib", "vram_peak_mib",
                          "correct", "sent_to_large", "tokens", "latency_mean_s", "latency_p95_s",
                          "answered", "exit_code"])
        return self.run_table_model

    def _servers_up(self, strategy, remote_dir):
        r, log = self.remote, f"{remote_dir}/hold.log"
        r.run(f"rm -rf {q(remote_dir)} && mkdir -p {q(remote_dir)}")
        self.server_pid = r.start_background(
            f"exec {config.REMOTE_PYTHON} ollama_server.py hold {strategy}",
            cwd=config.REMOTE_DIR, log_file=log, pid_file=f"{remote_dir}/hold.pid")
        if not r.wait_for_line(self.server_pid, log, "READY", config.SERVER_READY_TIMEOUT_S):
            tail = r.run(f"tail -n 30 {q(log)}", check=False).stdout
            self._servers_down()
            raise RuntimeError(f"Strategy {strategy} did not come up on the host:\n{tail}")

    def _servers_down(self):
        if self.server_pid is None:
            return
        pid, r = self.server_pid, self.remote
        self.server_pid = None
        r.run(f"kill -TERM -{pid} 2>/dev/null; true", check=False)
        if not r.wait_for_exit(pid, 60):
            output.console_log("ollama_server.py hold did not stop, force-killing")
            r.run(f"kill -KILL -{pid} 2>/dev/null; pkill -u \"$(id -un)\" -x ollama; true", check=False)

    def _check_same_commit(self):
        """Host must run the same code as the laptop: the host only has what's committed + pulled there."""
        local = subprocess.run(["git", "-C", str(HERE), "rev-parse", "HEAD"], capture_output=True, text=True)
        remote = self.remote.run(f"git -C {q(config.REMOTE_DIR)} rev-parse HEAD", check=False)
        if local.returncode or remote.returncode:
            output.console_log("WARNING: could not compare git commits of laptop and host, skipping check")
            return
        lh, rh = local.stdout.strip(), remote.stdout.strip()
        dirty = subprocess.run(["git", "-C", str(HERE), "status", "--porcelain", "--", *HOST_SIDE_FILES],
                               capture_output=True, text=True).stdout.strip()
        if dirty:
            output.console_log(f"WARNING: uncommitted changes in host-side files, the host won't have them:\n{dirty}")
        if lh != rh:
            msg = (f"host checkout is at {rh[:10]}, laptop at {lh[:10]}. Push your commit and update the host:\n"
                   f"  ssh {config.REMOTE_HOST} 'git -C {config.REMOTE_DIR} pull --ff-only'")
            if config.REQUIRE_SAME_COMMIT:
                raise RuntimeError(msg)
            output.console_log(f"WARNING: {msg}")

    def _push_inputs(self):
        """questions.jsonl and the router are not in git: copy the laptop's versions to the host every time."""
        if not config.QUESTIONS_FILE.is_file():
            raise RuntimeError(f"{config.QUESTIONS_FILE} missing. Create it first:\n"
                               f"  uv run download_dataset && uv run python llm-routing/sample_test_questions.py --n 100 --seed 42")
        self.remote.push([config.QUESTIONS_FILE], config.REMOTE_DIR)
        router = config.router_model_path()
        if router.is_file():
            self.remote.push([router], posixpath.join(posixpath.dirname(config.REMOTE_DIR.rstrip("/")), "data", "router_model"))
            output.console_log(f"Pushed questions.jsonl and {router.name} to the host")
        else:
            output.console_log("Pushed questions.jsonl; no router on the laptop, the host's own router file is used")
        return router if router.is_file() else None

    def _check_energibridge(self):
        """Real 2 s measurement: catches missing permissions and unexpected column names before run 1."""
        chk = f"{config.REMOTE_RESULTS_DIR}/energibridge_check.csv"
        self.remote.run(f"{config.ENERGIBRIDGE_CMD} --gpu -o {q(chk)} -- sleep 2", timeout=60)
        cols = self.remote.run(f"head -n 1 {q(chk)}").stdout.strip().split(",")
        missing = [c for c in EB_COLUMNS if c not in cols]
        if not any(c in cols for c in CPU_ENERGY_COLUMNS):
            missing.append(" or ".join(CPU_ENERGY_COLUMNS))
        if missing:
            raise RuntimeError(f"EnergiBridge output lacks {missing}. Columns it wrote: {cols}")

    def before_experiment(self):
        r = self.remote
        output.console_log(f"Pre-flight checks on {config.REMOTE_HOST}")
        r.run(f"test -d {q(config.REMOTE_DIR)} && test -x {q(config.REMOTE_PYTHON)}")
        self._check_same_commit()
        pushed_router = self._push_inputs()
        out = r.run(f"cd {q(config.REMOTE_DIR)} && {config.REMOTE_PYTHON} run_queries.py check-router").stdout.strip()
        output.console_log(out)
        if pushed_router is not None and pushed_router.name not in out:
            output.console_log(f"WARNING: host picked a different router than the laptop's {pushed_router.name}")
        r.run(f"mkdir -p {q(config.REMOTE_RESULTS_DIR)}")
        self._check_energibridge()
        busy = r.run("nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader",
                     check=False).stdout.strip()
        if busy:
            output.console_log(f"WARNING: GPUs already in use, this pollutes energy numbers:\n{busy}")

        output.console_log(f"Warming up the host for {config.WARMUP_S}s")
        warm = f"{config.REMOTE_RESULTS_DIR}/warmup"
        self._servers_up("R", warm)
        r.run(f"cd {q(config.REMOTE_DIR)} && timeout {config.WARMUP_S} "
              f"{config.REMOTE_PYTHON} run_queries.py R /dev/null",
              check=False, timeout=config.WARMUP_S + 60)
        self._servers_down()

    def start_run(self, context):
        self.remote_run_dir = f"{config.REMOTE_RESULTS_DIR}/{context.run_dir.name}"
        self._servers_up(context.execute_run["strategy"], self.remote_run_dir)

    def interact(self, context):
        d, strategy = self.remote_run_dir, context.execute_run["strategy"]
        cmd = (f"{config.ENERGIBRIDGE_CMD} --gpu -o {q(d)}/energibridge.csv -- "
               f"timeout {config.RUN_TIMEOUT_S} {config.REMOTE_PYTHON} run_queries.py {strategy} {q(d)}/queries.csv; "
               f"echo $? > {q(d)}/exit_code")
        pid = self.remote.start_background(cmd, cwd=config.REMOTE_DIR,
                                           log_file=f"{d}/energibridge.log", pid_file=f"{d}/eb.pid")
        if not self.remote.wait_for_exit(pid, config.RUN_TIMEOUT_S + 120):
            raise RuntimeError(f"{context.run_dir.name}: energibridge still running after timeout")

    def stop_run(self, context):
        self._servers_down()

    def populate_run_data(self, context):
        self.remote.fetch_dir(self.remote_run_dir, context.run_dir)
        eb = pd.read_csv(context.run_dir / "energibridge.csv")
        qs = pd.read_csv(context.run_dir / "queries.csv")
        cpu_col = next((c for c in CPU_ENERGY_COLUMNS if c in eb.columns), None)
        if cpu_col is None:
            raise KeyError(f"No CPU energy column in energibridge.csv, got: {list(eb.columns)}")
        seconds = eb["Time"].diff().fillna(0) / 1000
        cpu_steps = eb[cpu_col].diff().fillna(0)
        return {
            "cpu_energy_j":   cpu_steps[cpu_steps >= 0].sum(),
            "gpu_energy_j":   ((eb["GPU0_POWER (mWatts)"] + eb["GPU1_POWER (mWatts)"]) / 1000 * seconds).sum(),
            "runtime_s":      seconds.sum(),
            "gpu0_util_pct":  eb["GPU0_USAGE"].mean(),
            "gpu1_util_pct":  eb["GPU1_USAGE"].mean(),
            "ram_peak_mib":   eb["USED_MEMORY"].max() / 2**20,
            "vram_peak_mib":  (eb["GPU0_MEMORY_USED"] + eb["GPU1_MEMORY_USED"]).max(),
            "correct":        qs["correct"].sum(),
            "sent_to_large":  (qs["model"] == "large").sum(),
            "tokens":         qs["completion_tokens"].sum(),
            "latency_mean_s": qs["latency_s"].mean(),
            "latency_p95_s":  qs["latency_s"].quantile(0.95),
            "answered":       len(qs),
            "exit_code":      (context.run_dir / "exit_code").read_text().strip(),
        }

    def after_experiment(self):
        self._servers_down()
