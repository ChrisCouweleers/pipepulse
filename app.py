from __future__ import annotations

from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import repository
from src.pipeline import run_commerce_pipeline, FAILURE_MODES

st.set_page_config(page_title="PipePulse", page_icon="◫", layout="wide")
repository.initialize_database()

# Small amount of styling to keep the app dense and operational rather than marketing-oriented.
st.markdown("""
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1450px;}
[data-testid="stMetric"] {border: 1px solid rgba(255,255,255,.09); padding: .7rem .85rem; border-radius: .45rem;}
[data-testid="stMetricLabel"] {font-size: .78rem;}
.small-note {color:#8b95a7;font-size:.82rem;}
.section-rule {border-top:1px solid rgba(255,255,255,.08); margin: .35rem 0 1rem;}
</style>
""", unsafe_allow_html=True)

st.title("PipePulse")
st.caption("ELT pipeline operations & observability · synthetic portfolio environment")

# ---------------- Sidebar controls ----------------
with st.sidebar:
    st.header("Controls")
    pipelines = repository.dataframe("select distinct pipeline_name from pipeline_runs order by pipeline_name")["pipeline_name"].tolist()
    selected_pipeline = st.selectbox("Pipeline", pipelines, index=pipelines.index("commerce_daily") if "commerce_daily" in pipelines else 0)
    lookback = st.selectbox("History window", [7,14,30,45], index=2, format_func=lambda x:f"Last {x} days")
    status_filter = st.multiselect("Run status", ["success","failed"], default=["success","failed"])

    st.divider()
    st.subheader("Run demo pipeline")
    failure_label = st.selectbox("Failure injection", list(FAILURE_MODES.keys()), help="Optional: deliberately corrupt or break one stage to demonstrate observability and debugging.")
    run_clicked = st.button("Run pipeline", type="primary", use_container_width=True)
    st.caption("Executes the local `commerce_daily` ELT flow and records the new run in DuckDB.")

if run_clicked:
    with st.spinner("Executing ELT pipeline..."):
        result = run_commerce_pipeline(FAILURE_MODES[failure_label])
    if result["status"] == "success":
        st.success(f"Run {result['run_id']} succeeded in {result['duration_seconds']:.2f}s.")
    else:
        st.error(f"Run {result['run_id']} failed: {result['error_message']}")

cutoff = datetime.now() - timedelta(days=lookback)
placeholders = ",".join(["?"]*len(status_filter)) if status_filter else "''"
params = [selected_pipeline, cutoff] + status_filter
runs = repository.dataframe(f"""
    select * from pipeline_runs
    where pipeline_name=? and started_at >= ?
      and status in ({placeholders})
    order by started_at desc
""", params) if status_filter else repository.dataframe("select * from pipeline_runs where 1=0")

all_recent = repository.dataframe("""
    select * from pipeline_runs
    where started_at >= ?
    order by started_at desc
""", [cutoff])

# ---------------- Tabs ----------------
overview_tab, runs_tab, quality_tab, lineage_tab, warehouse_tab = st.tabs([
    "Overview","Runs","Data Quality","Lineage","Warehouse"
])

with overview_tab:
    if runs.empty:
        st.info("No runs match the selected filters.")
    else:
        success_rate = (runs["status"]=="success").mean()
        failures = int((runs["status"]=="failed").sum())
        median_runtime = runs["duration_seconds"].median()
        latest = runs.iloc[0]
        p95_runtime = runs["duration_seconds"].quantile(.95)

        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Success rate", f"{success_rate:.1%}")
        c2.metric("Failed runs", f"{failures:,}")
        c3.metric("Median runtime", f"{median_runtime:.1f}s")
        c4.metric("P95 runtime", f"{p95_runtime:.1f}s")
        c5.metric("Latest rows", f"{int(latest['rows_loaded']):,}")

        st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)

        left,right = st.columns([1.7,1])
        with left:
            timeline = runs.sort_values("started_at")
            fig = px.line(timeline,x="started_at",y="duration_seconds",markers=True,color="status",
                          title="Runtime trend", labels={"duration_seconds":"Seconds","started_at":"Run time"})
            fig.update_layout(height=330,legend_title_text="Status",margin=dict(l=10,r=10,t=45,b=10))
            st.plotly_chart(fig,use_container_width=True)
        with right:
            status_counts = runs.groupby("status",as_index=False).size()
            fig = px.bar(status_counts,x="status",y="size",color="status",title="Runs by status",
                         labels={"size":"Runs","status":"Status"})
            fig.update_layout(height=330,showlegend=False,margin=dict(l=10,r=10,t=45,b=10))
            st.plotly_chart(fig,use_container_width=True)

        st.subheader("Latest run")
        latest_run_id = str(latest["run_id"])
        latest_steps = repository.dataframe("select * from pipeline_steps where run_id=? order by step_order",[latest_run_id])
        cols = st.columns(len(latest_steps)) if len(latest_steps) else []
        for col,(_,step) in zip(cols,latest_steps.iterrows()):
            with col:
                icon = "✓" if step["status"]=="success" else ("✕" if step["status"]=="failed" else "–")
                st.markdown(f"**{icon} {step['step_name']}**")
                st.caption(f"{step['layer']} · {float(step['duration_seconds']):.2f}s")

        st.subheader("Cross-pipeline health")
        cross = all_recent.groupby("pipeline_name").agg(
            runs=("run_id","count"),
            success_rate=("status",lambda s:(s=="success").mean()),
            median_runtime=("duration_seconds","median"),
            failures=("status",lambda s:(s=="failed").sum()),
            latest_run=("started_at","max")
        ).reset_index()
        cross["success_rate"] = cross["success_rate"].map(lambda x:f"{x:.1%}")
        cross["median_runtime"] = cross["median_runtime"].map(lambda x:f"{x:.1f}s")
        st.dataframe(cross,use_container_width=True,hide_index=True)

with runs_tab:
    st.subheader("Run history")
    display_cols=["run_id","started_at","status","trigger_type","duration_seconds","rows_loaded","freshness_minutes","error_message"]
    st.dataframe(runs[display_cols],use_container_width=True,hide_index=True)

    if not runs.empty:
        selected_run = st.selectbox("Inspect run", runs["run_id"].tolist(), key="inspect_run")
        run_info = repository.dataframe("select * from pipeline_runs where run_id=?",[selected_run]).iloc[0]
        steps = repository.dataframe("select * from pipeline_steps where run_id=? order by step_order",[selected_run])

        a,b,c,d = st.columns(4)
        a.metric("Status", str(run_info["status"]).upper())
        b.metric("Duration", f"{float(run_info['duration_seconds']):.2f}s")
        c.metric("Rows loaded", f"{int(run_info['rows_loaded']):,}")
        d.metric("Freshness", f"{int(run_info['freshness_minutes']):,} min")

        fig = px.bar(steps,x="duration_seconds",y="step_name",orientation="h",color="status",
                     title="Step trace", labels={"duration_seconds":"Seconds","step_name":"Step"})
        fig.update_layout(height=max(300,90+45*len(steps)),margin=dict(l=10,r=10,t=45,b=10),showlegend=False)
        st.plotly_chart(fig,use_container_width=True)
        st.dataframe(steps[["step_order","step_name","layer","status","duration_seconds","rows_in","rows_out","target","error_message"]],
                     use_container_width=True,hide_index=True)
        if str(run_info["error_message"]).strip():
            st.error(str(run_info["error_message"]))

        csv_bytes = steps.to_csv(index=False).encode("utf-8")
        st.download_button("Download step log CSV",csv_bytes,file_name=f"{selected_run}_steps.csv",mime="text/csv")

with quality_tab:
    st.subheader("Quality rules")
    q = repository.dataframe("""
        select q.*, r.pipeline_name, r.started_at
        from quality_results q
        join pipeline_runs r using(run_id)
        where r.started_at >= ?
        order by r.started_at desc
    """,[cutoff])
    if q.empty:
        st.info("No quality results in the selected history window.")
    else:
        summary = q.groupby("check_name").agg(
            executions=("run_id","count"),
            failures=("status",lambda s:(s=="failed").sum()),
            last_run=("started_at","max")
        ).reset_index()
        summary["pass_rate"] = 1 - summary["failures"] / summary["executions"]
        summary["pass_rate"] = summary["pass_rate"].map(lambda x:f"{x:.1%}")
        st.dataframe(summary[["check_name","executions","failures","pass_rate","last_run"]],use_container_width=True,hide_index=True)

        failed = q[q["status"]=="failed"].copy()
        st.subheader("Recent failures")
        if failed.empty:
            st.success("No failed quality checks in this window.")
        else:
            st.dataframe(failed[["started_at","pipeline_name","run_id","check_name","severity","failed_rows","detail"]].head(100),
                         use_container_width=True,hide_index=True)

        by_rule = q.assign(failed=(q["status"]=="failed").astype(int)).groupby("check_name",as_index=False)["failed"].mean()
        by_rule["pass_rate"] = 1-by_rule["failed"]
        fig=px.bar(by_rule.sort_values("pass_rate"),x="pass_rate",y="check_name",orientation="h",title="Quality pass rate by rule")
        fig.update_xaxes(tickformat=".0%",range=[0,1])
        fig.update_layout(height=360,margin=dict(l=10,r=10,t=45,b=10))
        st.plotly_chart(fig,use_container_width=True)

with lineage_tab:
    st.subheader("Warehouse lineage")
    st.caption("The runnable demo uses ELT: source extracts are loaded to raw tables first, then transformed inside DuckDB with SQL.")
    dot = """
    digraph G {
      rankdir=LR;
      graph [bgcolor="transparent", pad="0.3", nodesep="0.45", ranksep="0.65"];
      node [shape=box, style="rounded,filled", fillcolor="#171d28", color="#465064", fontcolor="#e7ebf3", fontname="Arial"];
      edge [color="#6f7b8f", arrowsize="0.7"];
      crm [label="CRM customers CSV"];
      commerce [label="Commerce orders CSV"];
      products [label="Product catalog CSV"];
      rawc [label="raw_customers"];
      rawo [label="raw_orders"];
      rawp [label="raw_products"];
      dimc [label="dim_customers"];
      dimp [label="dim_products"];
      fact [label="fct_orders"];
      daily [label="mart_daily_revenue"];
      value [label="mart_customer_value"];
      dq [label="quality_results", shape=ellipse];
      crm -> rawc -> dimc;
      commerce -> rawo -> fact;
      products -> rawp -> dimp;
      dimc -> daily; dimp -> daily; fact -> daily;
      dimc -> value; fact -> value;
      rawc -> dq [style=dashed]; rawo -> dq [style=dashed]; daily -> dq [style=dashed];
    }
    """
    st.graphviz_chart(dot,use_container_width=True)

    st.subheader("Transformation layers")
    layers = pd.DataFrame([
        ["Source","crm_customers.csv / commerce_orders.csv / product_catalog.csv","Synthetic operational extracts"],
        ["Raw","raw_customers / raw_orders / raw_products","Loaded with source shape preserved"],
        ["Dimension","dim_customers / dim_products","Cleaned conformed descriptive entities"],
        ["Fact","fct_orders","Order-grain analytical event table"],
        ["Mart","mart_daily_revenue / mart_customer_value","BI-ready business aggregates"],
        ["Observability","pipeline_runs / pipeline_steps / quality_results","Operational metadata and rule outcomes"],
    ],columns=["Layer","Objects","Purpose"])
    st.dataframe(layers,use_container_width=True,hide_index=True)

with warehouse_tab:
    st.subheader("Warehouse explorer")
    tables = repository.list_warehouse_tables()
    if tables.empty:
        st.info("Warehouse tables have not been built yet. Run the `commerce_daily` pipeline from the sidebar.")
    else:
        table_name=st.selectbox("Table",tables["table_name"].tolist())
        schema=repository.table_schema(table_name)
        preview=repository.table_preview(table_name,100)
        count_df=repository.dataframe(f"select count(*) as rows from {table_name}")
        st.caption(f"{int(count_df.iloc[0]['rows']):,} rows")
        c1,c2=st.columns([.9,1.6])
        with c1:
            st.markdown("**Schema**")
            st.dataframe(schema,use_container_width=True,hide_index=True,height=320)
        with c2:
            st.markdown("**Preview**")
            st.dataframe(preview,use_container_width=True,hide_index=True,height=320)

        st.subheader("Example analytical queries")
        queries={
            "Revenue by region":"""select region, round(sum(net_revenue),2) as revenue
from mart_daily_revenue
group by region
order by revenue desc""",
            "Top customers":"""select customer_name, segment, region, lifetime_orders, lifetime_revenue
from mart_customer_value
order by lifetime_revenue desc
limit 20""",
            "Daily revenue trend":"""select order_date, round(sum(net_revenue),2) as revenue
from mart_daily_revenue
group by order_date
order by order_date""",
        }
        qname=st.selectbox("Query",list(queries.keys()))
        st.code(queries[qname],language="sql")
        if st.button("Execute query"):
            result=repository.dataframe(queries[qname])
            st.dataframe(result,use_container_width=True,hide_index=True)
