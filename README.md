# PipePulse — ELT Operations & Observability

PipePulse is a portfolio project that behaves like an internal data-engineering tool. It runs a small ELT pipeline, writes operational metadata, executes data-quality checks, and exposes the results through an interactive Streamlit dashboard.

## Live demo

[Open PipePulse](https://pipepulse.streamlit.app/)

The app runs on Streamlit Community Cloud and may take a moment to wake up and load on the first visit after a period of inactivity.

## What it demonstrates

- Python ELT orchestration
- Raw → transformed → mart warehouse layers
- SQL transformations inside DuckDB
- Pipeline run / step metadata
- Data quality and freshness checks
- Failure injection and exception handling
- Operational BI for data pipelines
- Warehouse inspection and query exploration

## Architecture

```text
CRM CSV ───────┐
               ├─> RAW layer ─> DIM / FACT models ─> MARTS
Commerce CSV ──┤                 │                    │
Product CSV ───┘                 └─ SQL transforms ──┘
                                      │
                                      ▼
                               Data quality checks
                                      │
                                      ▼
                              Operational metadata
                                      │
                                      ▼
                                 PipePulse UI
```

The included demo uses local CSV sources and DuckDB so a reviewer can clone and run it without cloud credentials. The architecture intentionally mirrors patterns that can later target Snowflake, BigQuery, Redshift, or Databricks.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The first launch creates `data/runtime/pipepulse.duckdb` and imports historical demo metadata. Use **Run pipeline** in the sidebar to execute a real local ELT run.

## Demo workflow

1. Open **Overview** to inspect pipeline health.
2. Use **Run pipeline** with no failure injection.
3. Run again with **Duplicate customer key** or **Negative order amount**.
4. Open **Runs** and inspect the failed trace.
5. Open **Data Quality** to see the rule failure.
6. Open **Warehouse** to inspect the raw, dimensional, fact, and mart tables.

## ELT design

The runnable `commerce_daily` flow follows an ELT pattern:

1. Extract source files into Python dataframes.
2. Load raw tables into DuckDB with minimal reshaping.
3. Transform dimensions, facts, and marts with warehouse SQL.
4. Run quality checks against the loaded/transformed data.
5. Persist run, step, and quality metadata for observability.

## Repository map

```text
app.py                       Streamlit operations UI
src/pipeline.py              ELT runner and failure injection
src/repository.py            DuckDB metadata / warehouse access
src/quality.py               Data-quality rules
sql/                         Warehouse transformation SQL
data/sources/                Synthetic source-system extracts
data/seed/                   Historical operational metadata
scripts/generate_demo_data.py Rebuild demo source/seed data
```

## Portfolio note

All business data is synthetic. The project is intended to demonstrate the engineering decisions, data model, operational controls, and debugging workflow rather than claim a production deployment.

## Local helper scripts

For Windows PowerShell, the repository includes convenience scripts:

```powershell
.\scripts\setup.ps1   # create .venv and install dependencies
.\scripts\run.ps1     # start Streamlit
.\scripts\check.ps1   # run tests and a successful pipeline smoke test
```
