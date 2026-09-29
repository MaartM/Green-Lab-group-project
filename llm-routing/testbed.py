"""
Run commands on the testbed and copy files to and from it, over SSH.

Experiment Runner runs on the laptop and reaches the testbed only through
these functions. Remote paths are relative to config.TESTBED_DIR.
"""

import shlex
import subprocess
from pathlib import Path

import config


def run(*command: str | Path) -> str:
    """Run a command in TESTBED_DIR on the testbed and return its output."""
    remote = f"cd {config.TESTBED_DIR} && {shlex.join(map(str, command))}"
    result = subprocess.run(["ssh", config.TESTBED_HOST, remote],
                            check=True, stdout=subprocess.PIPE, text=True)
    return result.stdout


def copy_to(paths: list[Path]) -> None:
    """Copy local files into TESTBED_DIR, creating it if needed."""
    subprocess.run(["ssh", config.TESTBED_HOST, f"mkdir -p {config.TESTBED_DIR}"], check=True)
    subprocess.run(["scp", "-O", "-q", *map(str, paths),
                    f"{config.TESTBED_HOST}:{config.TESTBED_DIR}/"], check=True)


def copy_from(remote_dir: str, local_dir: Path) -> None:
    """Copy every file in a testbed directory into a local directory."""
    subprocess.run(["scp", "-O", "-q",
                    f"{config.TESTBED_HOST}:{config.TESTBED_DIR}/{remote_dir}/*", str(local_dir)],
                   check=True)
