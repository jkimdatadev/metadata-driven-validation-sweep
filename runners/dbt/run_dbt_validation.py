"""
Run the dbt validation runner end to end: generate tests, run them, load results.

Usage:
    1. Activate the dbt-databricks virtual environment.
    2. Set DATABRICKS_HOST, DATABRICKS_HTTP_PATH and DATABRICKS_TOKEN.
    3. From runners/dbt, run: python run_dbt_validation.py
"""
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent


def run(step_name, command, allowed_exit_codes=(0,)):
    """Run one step and stop the whole sequence if it exits unexpectedly."""
    print(f"\n=== {step_name} ===")
    exit_code = subprocess.run(command, cwd=PROJECT_DIR).returncode
    if exit_code not in allowed_exit_codes:
        sys.exit(f"{step_name} failed with exit code {exit_code}; stopping.")
    return exit_code


run("Generate tests from the registry", [sys.executable, "generate_sources.py"])

# dbt exits with 1 when tests fail, which is an expected outcome for defect tables;
# only exit code 2 means dbt itself could not run
test_exit_code = run("Run dbt tests", ["dbt", "test"], allowed_exit_codes=(0, 1))

run("Load results into the results table", [sys.executable, "load_results.py"])

outcome = "all tests passed" if test_exit_code == 0 else "some tests failed, results recorded"
print(f"\nDone: {outcome}.")