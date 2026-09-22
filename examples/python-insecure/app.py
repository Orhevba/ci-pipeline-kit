"""DELIBERATELY INSECURE - do not copy. This exists only so the kit's CI can prove that python-security-scan.yml still WRITES ITS REPORT
when the tools find problems (they exit non-zero, and a step running under `bash -e` would otherwise stop before reporting)."""
import subprocess


def run(command: str) -> int:
    return subprocess.call(command, shell=True)   # bandit B602: shell=True with a caller-supplied string
