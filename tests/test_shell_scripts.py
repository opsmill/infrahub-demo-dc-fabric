import subprocess

# import pytest
import os


def test_topology_generator_script():
    script_path = "docs/docs/code_snippets/0002_shell_run_generator.sh"
    # Execute from project root directory
    result = subprocess.run(
        f"bash {script_path}",
        shell=True,
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(__file__)),
    )
    assert result.returncode == 0
