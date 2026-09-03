# PipePulse architecture

## Goal

PipePulse demonstrates the mechanics and operational concerns of a small ELT platform without requiring external infrastructure. The local stack is intentionally portable, but the layers mirror patterns used with cloud warehouses and orchestrators.

## Data flow

```text
Synthetic source extracts
  ├─ CRM customers
  ├─ Product catalog
  └─ Commerce orders
          │
          ▼
     Python extract
          │
          ▼
      RAW TABLES
  raw_customers
  raw_products
  raw_orders
          │
          ▼
   SQL TRANSFORMS
          │
    ┌─────┴──────┐
    ▼            ▼
DIMENSIONS      FACTS
customers       orders
products
    └─────┬──────┘
          ▼
        MARTS
 daily revenue
 customer value
          │
          ├──────────────► Warehouse explorer
          │
          ▼
  DATA QUALITY RULES
          │
          ▼
 OPERATIONAL METADATA
  pipeline_runs
  pipeline_steps
  quality_results
          │
          ▼
      Streamlit UI
```

## Execution model

`run_commerce_pipeline()` orchestrates six steps:

1. Extract source CSVs into pandas DataFrames.
2. Load minimally reshaped raw tables into DuckDB.
3. Execute dimension SQL.
4. Execute fact SQL.
5. Build analytics marts.
6. Execute data-quality checks and persist their results.

Each step records timing, status, input/output row counts, target, and any error. A failed step causes downstream stages to be recorded as skipped.

## Persistence

The application creates a disposable local DuckDB database under `data/runtime/`. On initialization, committed seed files provide historical run metadata so the UI is useful immediately after clone.

The runtime database is intentionally not committed.

## Failure injection

The demo exposes controlled failure modes so reviewers can see observability behavior rather than only a green dashboard. Failures are applied to in-memory DataFrames or execution flow and do not rewrite the committed source extracts.

## Boundaries

This project currently avoids external cloud dependencies. Future versions can add optional integrations such as an API source, orchestration framework, or Snowflake target, but the default portfolio demo should remain simple to clone and run.
