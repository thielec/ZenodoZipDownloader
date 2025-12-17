"""Tests for the zenodozipdownloader CLI entry point."""

import subprocess
import sys


def test_cli_help():
    """Running `python -m zenodozipdownloader --help` should exit 0 and print help."""
    res = subprocess.run(
        [sys.executable, "-m", "zenodozipdownloader", "--help"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "Download files from Zenodo ZIP records." in res.stdout
