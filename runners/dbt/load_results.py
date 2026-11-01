"""Load dbt test results into the central validation results table.

Reads target/run_results.json and target/manifest.json from the last dbt test run,
combines each registry entry's pk_null_rows and pk_extra_rows tests into one row,
and appends the rows to validation_sweep.results.validation_results with method 'dbt'.
Requires DATABRICKS_HOST, DATABRICKS_HTTP_PATH and DATABRICKS_TOKEN to be set.
"""
import json
import os
from datetime import date, datetime
from pathlib import Path

from databricks import sql

TARGET_DIR = Path(__file__).parent / "target"
RESULTS_TABLE = "validation_sweep.results.validation_results"
METHOD = "dbt"
TEST_TYPE = "pk_integrity"

COLUMNS = [
    "run_id", "run_ts", "run_date", "check_id", "method", "test_type", "table_name", "key_columns",
    "test_result", "row_count", "distinct_key_count", "null_key_count", "duplicate_count", "error_message",
    "last_data_change_ts", "age_hours", "max_age_hours",
]


def sql_literal(value):
    """Format a Python value as a Databricks SQL literal."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "array(" + ", ".join(sql_literal(v) for v in value) + ")"
    if isinstance(value, datetime):
        return f"timestamp'{value.isoformat()}'"
    if isinstance(value, date):
        return f"date'{value.isoformat()}'"
    escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


# Read dbt's output from the last run
run_results = json.loads((TARGET_DIR / "run_results.json").read_text())
manifest = json.loads((TARGET_DIR / "manifest.json").read_text())

if run_results.get("args", {}).get("which") != "test":
    raise SystemExit("The last dbt command was not 'dbt test'. Run dbt test, then load the results.")

run_id = run_results["metadata"]["invocation_id"]
run_ts = datetime.fromisoformat(run_results["metadata"]["generated_at"].replace("Z", "+00:00"))

# Group test results by registry entry, using the metadata the generator attached
checks = {}
for result in run_results["results"]:
    node = manifest["nodes"].get(result["unique_id"], {})
    meta = node.get("config", {}).get("meta") or node.get("meta") or {}
    if "metric" not in meta:
        print(f"Skipping {result['unique_id']}: no registry metadata")
        continue

    entry = checks.setdefault(
        (meta["table_name"], tuple(meta["key_columns"])),
        {"statuses": [], "metrics": {}, "errors": []},
    )
    entry["statuses"].append(result["status"])
    if result["status"] in ("pass", "fail"):
        entry["metrics"][meta["metric"]] = result["failures"] or 0
    else:
        message = result.get("message") or result["status"]
        entry["errors"].append(str(message).split("\n")[0][:500])

# Build one results row per registry entry
rows = []
for (table_name, key_columns), entry in checks.items():
    if entry["errors"]:
        test_result, metrics, error_message = "ERROR", {}, entry["errors"][0]
    elif "fail" in entry["statuses"]:
        test_result, metrics, error_message = "FAIL", entry["metrics"], None
    else:
        test_result, metrics, error_message = "PASS", entry["metrics"], None

    rows.append({
        "run_id": run_id,
        "run_ts": run_ts,
        "run_date": run_ts.date(),
        "check_id": "|".join([METHOD, TEST_TYPE, table_name, ",".join(key_columns)]),
        "method": METHOD,
        "test_type": TEST_TYPE,
        "table_name": table_name,
        "key_columns": list(key_columns),
        "test_result": test_result,
        "null_key_count": metrics.get("null_key_count"),
        "duplicate_count": metrics.get("duplicate_count"),
        "error_message": error_message,
    })

if not rows:
    raise SystemExit("No registry-driven test results found to load.")

# Write to the results table, skipping runs that were already loaded
with sql.connect(
    server_hostname=os.environ["DATABRICKS_HOST"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
) as connection:
    with connection.cursor() as cursor:
        cursor.execute(f"select count(*) from {RESULTS_TABLE} where run_id = {sql_literal(run_id)}")
        if cursor.fetchone()[0] > 0:
            raise SystemExit(f"Run {run_id} is already loaded; nothing to do.")

        values = ",\n".join(
            "(" + ", ".join(sql_literal(row.get(c)) for c in COLUMNS) + ")" for row in rows
        )
        cursor.execute(f"insert into {RESULTS_TABLE} ({', '.join(COLUMNS)}) values\n{values}")

print(f"Wrote {len(rows)} results for dbt run {run_id}")