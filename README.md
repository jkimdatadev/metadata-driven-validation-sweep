# Metadata-Driven Validation Sweep

Status: In Progress

Metadata-driven framework that automates schema-wide data validation without per-table code. Validates key uniqueness, null key values, and data freshness. Consolidates daily results into a single queryable table to support historical monitoring and alerting. Demonstrates three validation approaches: custom Python, Databricks Labs DQX, and dbt.

## Progress

- [x] Key registry for tables and their primary key columns
- [x] Custom Python runner that validates every registered table
- [x] Error handling: invalid registry entries are reported without stopping the run
- [ ] Central results table with daily history
- [ ] Freshness checks
- [ ] Databricks Labs DQX approach
- [ ] dbt approach

## How it works

Tables and their primary key columns are registered in a metadata table. The validation runner reads the registry and checks every active table for duplicate and null key values, so adding a table to the sweep only takes a new registry entry.

## Repository structure

- `setup/`: notebooks that prepare test data and the key registry
- `runners/python_native/`: custom Python validation runner
- `exploration/`: data exploration and error handling tests

## Running it

Developed on Databricks Free Edition using the TPC-H sample data. Run the notebooks in this order:

1. `setup/01_copy_source_tables`
2. `setup/02_create_pk_registry`
3. `runners/python_native/validate_primary_keys`
