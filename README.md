# Metadata-Driven Validation Sweep

Status: In Progress

Metadata-driven data validation framework that automates schema-wide validation without per-table code. A configurable key registry drives primary key uniqueness and null value checks across tables, and every run's results are stored in a single queryable table, with a view exposing the latest run for each validation method and test type.

Planned extensions include data freshness checks and a dbt-based validation approach.

Tech stack: Python, PySpark, SQL, Databricks, Delta Lake, Unity Catalog, Databricks Labs DQX

## Progress

- [x] Key registry for tables and their primary key columns
- [x] Custom Python runner that validates every registered table
- [x] Error handling: invalid registry entries are reported without stopping the run
- [x] Planted defect tables confirming duplicate and null key detection
- [x] Central results table with run history
- [x] Databricks Labs DQX approach
- [ ] Freshness checks
- [ ] dbt approach

## How it works

Tables and their primary key columns are registered in a metadata table. Each validation runner reads the registry, checks every active table for duplicate and null key values, and appends the results to a central results table. A view shows the latest run for each method, so adding a table to the sweep only takes a new registry entry.

```mermaid
flowchart TD
    A[("samples.tpch_sf1<br/>Read-only source")]
    B[("Dev tables<br/>setup/01, setup/04")]
    C[("pk_registry<br/>Tables and keys, setup/02")]
    D1["validate_primary_keys<br/>Python / PySpark runner"]
    D2["validate_primary_keys<br/>DQX runner"]
    E[("validation_results<br/>One row per check, per run")]
    F[("latest_validation_results<br/>View: latest run per method and test type")]

    A --> B
    B --> D1
    C --> D1
    B --> D2
    C --> D2
    D1 --> E
    D2 --> E
    E --> F

    classDef data fill:#eef0ff,stroke:#9298c8,color:#28335c
    classDef process fill:#e6f4ea,stroke:#5f9e6e,color:#1e3d27
    classDef view fill:#f3f3f7,stroke:#9298b7,color:#28335c,stroke-dasharray:4 2

    class A,B,C,E data
    class D1,D2 process
    class F view
```

## Example output

Sample results from validation runs. The `_dupes` and `_nulls` tables contain deliberately planted defects, and the ERROR row comes from the error handling test:

| table_name | key_columns | test_result | row_count | null_key_count | duplicate_count |
|---|---|---|---|---|---|
| `validation_sweep.dev.customer` | `c_custkey` | PASS | 150,000 | 0 | 0 |
| `validation_sweep.dev.partsupp` | `ps_partkey`, `ps_suppkey` | PASS | 800,000 | 0 | 0 |
| `validation_sweep.dev.customer_dupes` | `c_custkey` | FAIL | 150,005 | 0 | 5 |
| `validation_sweep.dev.partsupp_nulls` | `ps_partkey`, `ps_suppkey` | FAIL | 800,004 | 4 | 0 |
| `validation_sweep.dev.customer` | `c_invalidkey` | ERROR | — | — | — |

Clean copies pass, while the defect tables fail with the exact number of planted duplicates and null keys. The invalid key column (`c_invalidkey`) was temporarily added to the registry for testing; the runner records the error in `error_message` and continues validating the remaining tables. Metrics are unavailable for checks that encounter an error.

## Comparing approaches

Both runners read the same registry and write to the same results table, so their latest results can be compared directly:

| table_name | method | test_result | null_key_count | duplicate_count |
|---|---|---|---|---|
| `validation_sweep.dev.customer_dupes` | dqx | FAIL | 0 | 5 |
| `validation_sweep.dev.customer_dupes` | python_native | FAIL | 0 | 5 |
| `validation_sweep.dev.partsupp_nulls` | dqx | FAIL | 4 | 0 |
| `validation_sweep.dev.partsupp_nulls` | python_native | FAIL | 4 | 0 |

Findings so far:

- Both approaches detect the same planted defects with identical counts.
- DQX flags every row involved in a duplicate (10 rows for 5 duplicated keys), while the results table counts extra rows (5). The DQX runner converts its output so both methods report the same measure.
- DQX's uniqueness check treats null keys as distinct, so a separate not-null check is needed, matching how the Python runner reports nulls separately from duplicates.
- The Python runner computes all metrics in one aggregation, while the DQX runner applies its checks separately to attribute failures, which requires additional passes over each table.

## Repository structure

- `setup/`: notebooks that prepare test data, the key registry, the results table, and planted defects
- `runners/python_native/`: custom Python validation runner
- `runners/dqx/`: validation runner using Databricks Labs DQX
- `exploration/`: data exploration, DQX exploration, example result queries, and error handling tests

## Running it

Developed on Databricks Free Edition using the TPC-H sample data. Run the notebooks in this order:

1. `setup/01_copy_source_tables`
2. `setup/02_create_pk_registry`
3. `setup/03_create_results_table`
4. `setup/04_plant_pk_defects`
5. `runners/python_native/validate_primary_keys`
6. `runners/dqx/validate_primary_keys`

Each runner can also be run on its own after the setup notebooks.