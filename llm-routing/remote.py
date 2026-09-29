import shlex
import subprocess
import time
from pathlib import Path


SSH_FAILED = 255

def q(s) -> str:
    return shlex.quote(str(s))


class Remote:
    def __init__(self, host: str, connect_timeout: int = 10):
        self.host = host
        self.ssh_opts = ["-o", "BatchMode=yes",
                         "-o", f"ConnectTimeout={connect_timeout}",
                         "-o", "ServerAliveInterval=30"]

    def run(self, cmd: str, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess:
        proc = subprocess.run(["ssh", *self.ssh_opts, self.host, cmd],
                              capture_output=True, text=True, timeout=timeout)
        if check and proc.returncode != 0:
            raise RuntimeError(f"[remote] `{cmd}` exited {proc.returncode}\n{proc.stderr.strip()}")
        return proc

    def start_background(self, cmd: str, cwd: str, log_file: str, pid_file: str) -> int:
        """Start cmd detached on the host (survives SSH drops). Returned PID is also the process group id."""
        self.run(f"cd {q(cwd)} && {{ setsid nohup bash -c {q(cmd)} > {q(log_file)} 2>&1 < /dev/null & "
                 f"echo $! > {q(pid_file)}; }}")
        return int(self.run(f"cat {q(pid_file)}").stdout.strip())

    def _wait(self, remote_cmd: str, timeout_s: int) -> bool:
        """Run a blocking remote wait under a deadline. If the ssh link (or glgate) drops, reconnect and keep
        waiting: the remote job runs under setsid and doesn't care, so a dropped link is not a failed run."""
        deadline = time.monotonic() + timeout_s
        while (left := int(deadline - time.monotonic())) > 0:
            try:
                proc = self.run(f"timeout {left} {remote_cmd}", check=False, timeout=left + 30)
            except subprocess.TimeoutExpired:
                continue
            if proc.returncode != SSH_FAILED:
                return proc.returncode == 0
            print(f"[remote] ssh to {self.host} dropped while waiting ({proc.stderr.strip()[-200:]}), "
                  f"reconnecting in 10 s", flush=True)
            time.sleep(10)
        return False

    def wait_for_exit(self, pid: int, timeout_s: int) -> bool:
        """One idle ssh session until pid exits, no polling traffic. False on timeout."""
        return self._wait(f"tail --pid={pid} -f /dev/null", timeout_s)

    def wait_for_line(self, pid: int, log_file: str, line: str, timeout_s: int) -> bool:
        """Wait until `line` shows up in log_file. False on timeout or if pid died first."""
        loop = f"until grep -qx {q(line)} {q(log_file)}; do kill -0 {pid} 2>/dev/null || exit 1; sleep 1; done"
        return self._wait(f"bash -c {q(loop)}", timeout_s)

    def fetch_dir(self, remote_dir: str, local_dir: Path) -> None:
        local_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["scp", "-O", *self.ssh_opts, "-q", "-r", f"{self.host}:{remote_dir}/*", str(local_dir)],
                       check=True)

    def push(self, local_paths: list[Path], remote_dir: str) -> None:
        self.run(f"mkdir -p {q(remote_dir)}")
        subprocess.run(["scp", "-O", *self.ssh_opts, "-q", "-r", *map(str, local_paths), f"{self.host}:{remote_dir}/"],
                       check=True)
