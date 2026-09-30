"""
Run commands on the testbed and copy files to and from it, over SSH.

Experiment Runner runs on the laptop and reaches the testbed only through
these functions. Remote paths are relative to config.TESTBED_DIR.
"""

import os
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


def copy_to(paths: list[str]) -> None:
    """Copy files into TESTBED_ROOT, keeping their paths relative to the repository root."""
    archive = subprocess.Popen(["tar", "--no-xattrs", "-czf", "-", "-C", str(config.REPO_ROOT), *paths],
                               stdout=subprocess.PIPE, env={**os.environ, "COPYFILE_DISABLE": "1"})
    subprocess.run(["ssh", config.TESTBED_HOST,
                    f"mkdir -p {config.TESTBED_ROOT} && tar -xzf - -C {config.TESTBED_ROOT}"],
                   stdin=archive.stdout, check=True)
    archive.stdout.close()
    if archive.wait():
        raise subprocess.CalledProcessError(archive.returncode, "tar")


def copy_from(remote_dir: str, local_dir: Path) -> None:
    """Copy every file in a testbed directory into a local directory."""
    subprocess.run(["scp", "-O", "-q",
                    f"{config.TESTBED_HOST}:{config.TESTBED_DIR}/{remote_dir}/*", str(local_dir)],
                   check=True)
