# PipePulse prioritized backlog

This is a development backlog, not a promise that every feature belongs in the final portfolio project. Keep the project understandable and demoable.

## Priority 1 — strengthen the engineering demo

- Add a pipeline-run detail drawer/section with clearer failed-step diagnostics.
- Add data freshness status with warning/critical thresholds.
- Add row-count anomaly checks that compare a run with recent history.
- Add schema-drift detection for committed source extracts.
- Add tests for successful pipeline execution and failure injection.
- Add a compact pipeline status indicator for the most recent run of each pipeline.

## Priority 2 — make warehouse work more visible

- Show table row counts and last-refresh information in Warehouse Explorer.
- Add a model/data dictionary for raw, dimension, fact, and mart tables.
- Add a few curated SQL examples that answer realistic operational questions.
- Add metric definitions for daily revenue and customer value.

## Priority 3 — orchestration / production-flavored extension

- Add Prefect or Dagster as an optional orchestration layer.
- Add retry/backoff behavior to one realistic extract step.
- Add an API-backed source while retaining local fallback data.
- Add structured logs.
- Add optional dbt transformations if they clarify rather than duplicate the current SQL layer.

## Priority 4 — cloud extension

Only after the local project is polished:

- Add an optional Snowflake profile/target.
- Add GitHub Actions for tests and linting.
- Add scheduled demo data refresh if hosting permits it safely.

## UI direction

Keep the following primary areas:

- Overview
- Runs
- Data Quality
- Lineage
- Warehouse

Do not add marketing pages. New UI should support a concrete data-engineering workflow.
