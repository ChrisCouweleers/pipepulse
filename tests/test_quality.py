import pandas as pd
import duckdb

from src.quality import run_quality_checks


def _connection(duplicate=False, negative=False):
    con = duckdb.connect(":memory:")
    customers = pd.DataFrame([
        [1,"A","a@example.com","East","SMB","2026-01-01","2026-09-03 08:00:00"],
        [2,"B","b@example.com","West","Enterprise","2026-01-01","2026-09-03 08:00:00"],
    ],columns=["customer_id","customer_name","email","region","segment","created_at","source_updated_at"])
    if duplicate:
        customers = pd.concat([customers,customers.iloc[[0]]],ignore_index=True)
    amount = -10 if negative else 10
    orders = pd.DataFrame([
        [1,1,101,"2026-09-03",1,amount,amount,"paid","2026-09-03 08:00:00"]
    ],columns=["order_id","customer_id","product_id","order_date","quantity","unit_price","gross_amount","status","source_updated_at"])
    con.register("c",customers); con.register("o",orders)
    con.execute("create table raw_customers as select * from c")
    con.execute("create table raw_orders as select * from o")
    con.execute("create table mart_daily_revenue as select 1 as x")
    return con


def test_duplicate_customer_is_detected():
    con = _connection(duplicate=True)
    results = {x.check_name:x for x in run_quality_checks(con)}
    assert results["customer_id_unique"].status == "failed"


def test_negative_amount_is_detected():
    con = _connection(negative=True)
    results = {x.check_name:x for x in run_quality_checks(con)}
    assert results["order_amount_nonnegative"].status == "failed"
