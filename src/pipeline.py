from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, date
from pathlib import Path
from time import perf_counter
from uuid import uuid4
import pandas as pd

from . import repository
from .quality import run_quality_checks

BASE = Path(__file__).resolve().parents[1]
SOURCE_DIR = BASE / "data" / "sources"
SQL_DIR = BASE / "sql"

FAILURE_MODES = {
    "None": None,
    "Duplicate customer key": "duplicate_customer",
    "Negative order amount": "negative_order",
    "Transform error": "transform_error",
}


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def _step(run_id: str, order: int, name: str, layer: str, target: str, fn):
    started = datetime.now()
    t0 = perf_counter()
    try:
        rows_in, rows_out = fn()
        status = "success"
        error = ""
        result = None
    except Exception as exc:
        rows_in = 0
        rows_out = 0
        status = "failed"
        error = str(exc)
        result = exc
    ended = datetime.now()
    row = {
        "run_id": run_id,
        "step_order": order,
        "step_name": name,
        "layer": layer,
        "status": status,
        "started_at": started,
        "ended_at": ended,
        "duration_seconds": round(perf_counter() - t0, 3),
        "rows_in": int(rows_in),
        "rows_out": int(rows_out),
        "target": target,
        "error_message": error,
    }
    repository.insert_dataframe("pipeline_steps", pd.DataFrame([row]))
    if result:
        raise result
    return row


def run_commerce_pipeline(failure_mode: str | None = None) -> dict:
    repository.initialize_database()
    run_id = "live_" + uuid4().hex[:10]
    started = datetime.now()
    final_status = "success"
    error_message = ""
    rows_loaded = 0
    quality_results = []

    customers_holder = {}
    products_holder = {}
    orders_holder = {}

    def extract_sources():
        customers = pd.read_csv(SOURCE_DIR / "crm_customers.csv")
        products = pd.read_csv(SOURCE_DIR / "product_catalog.csv")
        orders = pd.read_csv(SOURCE_DIR / "commerce_orders.csv")

        if failure_mode == "duplicate_customer":
            customers = pd.concat([customers, customers.iloc[[0]]], ignore_index=True)
        elif failure_mode == "negative_order":
            orders.loc[orders.index[0], "gross_amount"] = -abs(float(orders.loc[orders.index[0], "gross_amount"]))
            orders.loc[orders.index[0], "unit_price"] = -abs(float(orders.loc[orders.index[0], "unit_price"]))

        customers_holder["df"] = customers
        products_holder["df"] = products
        orders_holder["df"] = orders
        total = len(customers) + len(products) + len(orders)
        return 0, total

    def load_raw():
        con = repository.connect()
        try:
            con.register("customers_df", customers_holder["df"])
            con.register("products_df", products_holder["df"])
            con.register("orders_df", orders_holder["df"])
            con.execute("create or replace table raw_customers as select * from customers_df")
            con.execute("create or replace table raw_products as select * from products_df")
            con.execute("create or replace table raw_orders as select * from orders_df")
            total = con.execute("select (select count(*) from raw_customers)+(select count(*) from raw_products)+(select count(*) from raw_orders)").fetchone()[0]
            return total, total
        finally:
            con.close()

    def transform_dimensions():
        con = repository.connect()
        try:
            sql = (SQL_DIR / "01_dimensions.sql").read_text(encoding="utf-8")
            con.execute(sql)
            out = con.execute("select (select count(*) from dim_customers)+(select count(*) from dim_products)").fetchone()[0]
            return len(customers_holder["df"]) + len(products_holder["df"]), out
        finally:
            con.close()

    def transform_facts():
        if failure_mode == "transform_error":
            raise RuntimeError("Injected demo failure: simulated warehouse transform error")
        con = repository.connect()
        try:
            sql = (SQL_DIR / "02_facts.sql").read_text(encoding="utf-8")
            con.execute(sql)
            out = con.execute("select count(*) from fct_orders").fetchone()[0]
            return len(orders_holder["df"]), out
        finally:
            con.close()

    def build_marts():
        con = repository.connect()
        try:
            sql = (SQL_DIR / "03_marts.sql").read_text(encoding="utf-8")
            con.execute(sql)
            out = con.execute("select (select count(*) from mart_daily_revenue)+(select count(*) from mart_customer_value)").fetchone()[0]
            return len(orders_holder["df"]), out
        finally:
            con.close()

    def quality_step():
        nonlocal quality_results
        con = repository.connect()
        try:
            quality_results = run_quality_checks(con)
        finally:
            con.close()
        qdf = pd.DataFrame([
            {
                "run_id": run_id,
                "check_name": q.check_name,
                "severity": q.severity,
                "status": q.status,
                "failed_rows": q.failed_rows,
                "detail": q.detail,
            }
            for q in quality_results
        ])
        repository.insert_dataframe("quality_results", qdf)
        failed_critical = [q for q in quality_results if q.status == "failed" and q.severity == "critical"]
        if failed_critical:
            names = ", ".join(q.check_name for q in failed_critical)
            raise RuntimeError(f"Critical data-quality checks failed: {names}")
        return len(quality_results), len(quality_results)

    steps = [
        (1,"Extract source files","Extract","source data",extract_sources),
        (2,"Load raw layer","Load","raw_*",load_raw),
        (3,"Build dimensions","Transform","dim_*",transform_dimensions),
        (4,"Build order fact","Transform","fct_orders",transform_facts),
        (5,"Build analytics marts","Transform","mart_*",build_marts),
        (6,"Run data quality","Quality","quality_results",quality_step),
    ]

    try:
        for order,name,layer,target,fn in steps:
            row = _step(run_id,order,name,layer,target,fn)
            rows_loaded = max(rows_loaded,row["rows_out"])
    except Exception as exc:
        final_status = "failed"
        error_message = str(exc)
        existing = repository.dataframe("select coalesce(max(step_order),0) as max_step from pipeline_steps where run_id=?", [run_id])
        max_step = int(existing.iloc[0]["max_step"])
        skipped = []
        for order,name,layer,target,_ in steps:
            if order > max_step:
                now = datetime.now()
                skipped.append({
                    "run_id":run_id,"step_order":order,"step_name":name,"layer":layer,"status":"skipped",
                    "started_at":now,"ended_at":now,"duration_seconds":0.0,"rows_in":0,"rows_out":0,
                    "target":target,"error_message":"Upstream step failed"
                })
        if skipped:
            repository.insert_dataframe("pipeline_steps", pd.DataFrame(skipped))

    ended = datetime.now()
    # Demo source file is intentionally stamped close to portfolio build date. This metric is operational metadata,
    # not a claim that the synthetic file is a live external source.
    max_source = pd.to_datetime(pd.read_csv(SOURCE_DIR / "commerce_orders.csv")["source_updated_at"]).max()
    freshness_minutes = max(0, int((datetime.now() - max_source.to_pydatetime()).total_seconds()/60))

    run_row = pd.DataFrame([{
        "run_id":run_id,
        "pipeline_name":"commerce_daily",
        "scheduled_for":date.today(),
        "started_at":started,
        "ended_at":ended,
        "status":final_status,
        "trigger_type":"manual",
        "duration_seconds":round((ended-started).total_seconds(),3),
        "rows_loaded":rows_loaded,
        "freshness_minutes":freshness_minutes,
        "error_message":error_message,
    }])
    repository.insert_dataframe("pipeline_runs", run_row)

    return {
        "run_id":run_id,
        "status":final_status,
        "duration_seconds":float(run_row.iloc[0]["duration_seconds"]),
        "rows_loaded":int(rows_loaded),
        "error_message":error_message,
    }
