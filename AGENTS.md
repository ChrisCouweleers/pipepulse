# PipePulse agent instructions

## Purpose
PipePulse is a portfolio project that demonstrates practical data-engineering and BI skills through a runnable ELT operations console. It should feel like an internal tool a data platform team would actually use.

Read `README.md` and `docs/ARCHITECTURE.md` before making architectural changes.

## Product guardrails
- Keep the product focused on the interactive engineering tool.
- Do **not** add a SaaS marketing homepage, pricing, testimonials, signup/login flows, billing, sales copy, or fake customer logos.
- Do **not** turn the project into a generic frontend showcase. UI work should improve observability, debugging, warehouse exploration, or data-quality workflows.
- Prefer dense, useful operational UI over decorative cards and oversized hero sections.
- All business data must remain clearly synthetic.
- The demo must remain runnable locally without cloud credentials unless the user explicitly asks to add a cloud integration.

## Technical stack
- Python
- Streamlit
- DuckDB
- pandas
- Plotly
- Graphviz
- SQL transformations in `sql/`
- pytest

## Repository map
- `app.py` — Streamlit UI only; keep business logic out of this file when practical.
- `src/pipeline.py` — ELT orchestration and controlled failure injection.
- `src/repository.py` — DuckDB initialization, persistence, and query helpers.
- `src/quality.py` — data-quality rules.
- `sql/` — warehouse transformation SQL.
- `data/sources/` — synthetic source extracts; treat these as source-system inputs.
- `data/seed/` — seeded historical operational metadata for the portfolio demo.
- `data/runtime/` — generated local warehouse; never commit it.
- `tests/` — automated tests.
- `docs/` — architecture and development roadmap.

## Architecture rules
- Preserve the source → raw → dimension/fact → mart → quality/observability flow.
- Put warehouse transformation logic in SQL files rather than embedding large SQL blocks in the UI.
- Persist operational metadata for pipeline runs, steps, and quality checks in DuckDB.
- Failure injection is a demonstration feature. It must not permanently corrupt files in `data/sources/`.
- Keep the runtime database disposable and reproducible from committed source/seed data.
- When adding a new pipeline stage, make it visible in run metadata and lineage.
- When adding a new quality rule, add or update automated tests.

## Development commands
Create the environment and install dependencies:

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

Run the app:

```bash
python -m streamlit run app.py
```

Run tests:

```bash
python -m pytest -q
```

Run a direct pipeline smoke test:

```bash
python -c "from src.pipeline import run_commerce_pipeline; print(run_commerce_pipeline())"
```

## Definition of done
For code changes, make a best effort to:
1. Run `python -m pytest -q`.
2. Run the direct pipeline smoke test when pipeline, repository, SQL, or quality logic changed.
3. Confirm `data/runtime/` remains ignored by git.
4. Update `README.md` or `docs/ARCHITECTURE.md` if behavior or architecture changed.
5. Keep the app usable immediately with the seeded demo data.

## Near-term direction
Use `docs/NEXT_STEPS.md` as the prioritized backlog. Do not implement the entire backlog unless asked; work one coherent task at a time.
