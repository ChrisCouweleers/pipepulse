from __future__ import annotations

from pathlib import Path
from typing import Iterable
import duckdb
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DB_PATH = BASE / "data" / "runtime" / "pipepulse.duckdb"
SEED_DIR = BASE / "data" / "seed"

RUN_COLUMNS = [
    "run_id","pipeline_name","scheduled_for","started_at","ended_at","status",
    "trigger_type","duration_seconds","rows_loaded","freshness_minutes","error_message"
]
STEP_COLUMNS = [
    "run_id","step_order","step_name","layer","status","started_at","ended_at",
    "duration_seconds","rows_in","rows_out","target","error_message"
]
QUALITY_COLUMNS = ["run_id","check_name","severity","status","failed_rows","detail"]


def connect(read_only: bool = False):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH), read_only=read_only)


def initialize_database() -> None:
    con = connect()
    con.execute("""
        create table if not exists pipeline_runs (
            run_id varchar primary key,
            pipeline_name varchar,
            scheduled_for date,
            started_at timestamp,
            ended_at timestamp,
            status varchar,
            trigger_type varchar,
            duration_seconds double,
            rows_loaded bigint,
            freshness_minutes integer,
            error_message varchar
        )
    """)
    con.execute("""
        create table if not exists pipeline_steps (
            run_id varchar,
            step_order integer,
            step_name varchar,
            layer varchar,
            status varchar,
            started_at timestamp,
            ended_at timestamp,
            duration_seconds double,
            rows_in bigint,
            rows_out bigint,
            target varchar,
            error_message varchar
        )
    """)
    con.execute("""
        create table if not exists quality_results (
            run_id varchar,
            check_name varchar,
            severity varchar,
            status varchar,
            failed_rows bigint,
            detail varchar
        )
    """)

    count = con.execute("select count(*) from pipeline_runs").fetchone()[0]
    if count == 0:
        for table, filename in [
            ("pipeline_runs","runs.csv"),
            ("pipeline_steps","steps.csv"),
            ("quality_results","quality_checks.csv"),
        ]:
            path = (SEED_DIR / filename).as_posix().replace("'", "''")
            con.execute(f"insert into {table} select * from read_csv_auto('{path}', header=true)")
    con.close()


def dataframe(query: str, params: Iterable | None = None) -> pd.DataFrame:
    con = connect()
    try:
        return con.execute(query, params or []).df()
    finally:
        con.close()


def execute(query: str, params: Iterable | None = None) -> None:
    con = connect()
    try:
        con.execute(query, params or [])
    finally:
        con.close()


def insert_dataframe(table: str, df: pd.DataFrame) -> None:
    if df.empty:
        return
    con = connect()
    try:
        con.register("incoming_df", df)
        con.execute(f"insert into {table} select * from incoming_df")
    finally:
        con.close()


def list_warehouse_tables() -> pd.DataFrame:
    return dataframe("""
        select table_name
        from information_schema.tables
        where table_schema='main'
          and table_name not in ('pipeline_runs','pipeline_steps','quality_results')
        order by table_name
    """)


def table_schema(table_name: str) -> pd.DataFrame:
    allowed = set(list_warehouse_tables()["table_name"].tolist())
    if table_name not in allowed:
        raise ValueError("Unknown table")
    return dataframe(f"describe {table_name}")


def table_preview(table_name: str, limit: int = 100) -> pd.DataFrame:
    allowed = set(list_warehouse_tables()["table_name"].tolist())
    if table_name not in allowed:
        raise ValueError("Unknown table")
    limit = max(1, min(int(limit), 500))
    return dataframe(f"select * from {table_name} limit {limit}")
