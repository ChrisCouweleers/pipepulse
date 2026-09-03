from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import duckdb


@dataclass
class QualityResult:
    check_name: str
    severity: str
    status: str
    failed_rows: int
    detail: str


def run_quality_checks(con: duckdb.DuckDBPyConnection) -> list[QualityResult]:
    checks: list[QualityResult] = []

    def add(name: str, severity: str, failed_rows: int, detail_ok: str, detail_fail: str):
        checks.append(QualityResult(
            check_name=name,
            severity=severity,
            status="passed" if failed_rows == 0 else "failed",
            failed_rows=int(failed_rows),
            detail=detail_ok if failed_rows == 0 else detail_fail,
        ))

    dup_customers = con.execute("""
        select count(*) from (
            select customer_id from raw_customers group by customer_id having count(*) > 1
        )
    """).fetchone()[0]
    add("customer_id_unique", "critical", dup_customers,
        "All customer IDs are unique.", f"{dup_customers} duplicated customer key(s) found.")

    dup_orders = con.execute("""
        select count(*) from (
            select order_id from raw_orders group by order_id having count(*) > 1
        )
    """).fetchone()[0]
    add("order_id_unique", "critical", dup_orders,
        "All order IDs are unique.", f"{dup_orders} duplicated order key(s) found.")

    negative = con.execute("select count(*) from raw_orders where gross_amount < 0 or unit_price < 0").fetchone()[0]
    add("order_amount_nonnegative", "critical", negative,
        "No negative order amounts found.", f"{negative} order row(s) contain negative monetary values.")

    invalid_status = con.execute("select count(*) from raw_orders where lower(status) not in ('paid','refunded')").fetchone()[0]
    add("order_status_accepted", "warning", invalid_status,
        "All order statuses are accepted values.", f"{invalid_status} order row(s) contain unexpected status values.")

    orphan_orders = con.execute("""
        select count(*)
        from raw_orders o
        left join raw_customers c on o.customer_id = c.customer_id
        where c.customer_id is null
    """).fetchone()[0]
    add("orders_customer_fk", "critical", orphan_orders,
        "All orders resolve to a customer.", f"{orphan_orders} order row(s) reference missing customers.")

    max_updated = con.execute("select max(cast(source_updated_at as timestamp)) from raw_orders").fetchone()[0]
    if max_updated is None:
        freshness_minutes = 999999
    else:
        freshness_minutes = int((datetime.now() - max_updated).total_seconds() / 60)
    freshness_failed = 1 if freshness_minutes > 60 * 24 * 3 else 0
    add("source_freshness", "warning", freshness_failed,
        f"Latest source record is {freshness_minutes:,} minutes old.",
        f"Source freshness SLA exceeded: latest record is {freshness_minutes:,} minutes old.")

    mart_rows = con.execute("select count(*) from mart_daily_revenue").fetchone()[0]
    add("revenue_mart_nonempty", "critical", 0 if mart_rows > 0 else 1,
        f"Revenue mart contains {mart_rows:,} row(s).", "Revenue mart is empty.")

    return checks
