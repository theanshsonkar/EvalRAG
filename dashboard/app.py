"""EvalRAG dashboard. Start with: streamlit run dashboard/app.py"""
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from evalrag import storage  # noqa: E402
from evalrag.compare import compare, quality_gate  # noqa: E402

st.set_page_config(page_title="EvalRAG", layout="wide")
st.title("EvalRAG: RAG / LLM evaluation dashboard")

conn = storage.connect()
runs = storage.list_runs(conn)
if not runs:
    st.info("No runs yet. Run `python -m evalrag.cli run --config configs/baseline.json --set-baseline`.")
    st.stop()

thresholds = json.loads((ROOT / "configs/thresholds.json").read_text())
base_id = storage.get_baseline_id(conn)
base = storage.run_summary(conn, base_id) if base_id else None
summaries = [storage.run_summary(conn, r["run_id"]) for r in runs]

# --- Run history -------------------------------------------------------------
st.header("Run history")
hist = []
for s in summaries:
    status, _ = quality_gate(s, thresholds, base)
    hist.append({"run": s["run_id"], "version": s["version"], "time (UTC)": s["started_at"],
                 "status": s["status"], "gate": status, "baseline": "yes" if s["is_baseline"] else "",
                 "avg latency (ms)": round(s["avg_latency_ms"], 2),
                 **{m: round(v, 3) for m, v in s["metrics"].items()}})
st.dataframe(pd.DataFrame(hist), hide_index=True, use_container_width=True)

trend = pd.DataFrame([{"run": s["run_id"], **s["metrics"]} for s in reversed(summaries)]).set_index("run")
st.subheader("Metric trend across runs")
st.line_chart(trend)

# --- Compare a run with the baseline -------------------------------------------------
st.header("Compare with baseline")
labels = {f"Run {s['run_id']} - {s['version']}": s for s in summaries}
cand = labels[st.selectbox("Candidate run", list(labels))]
status, reasons = quality_gate(cand, thresholds, base)
colour = {"PASS": "green", "WARN": "orange", "FAIL": "red"}[status]
st.markdown(f"### Quality gate: :{colour}[{status}]")
for r in reasons:
    st.write("- " + r)

c1, c2, c3 = st.columns(3)
c1.metric("Test cases", cand["num_cases"])
c2.metric("Errors", cand["errors"])
c3.metric("Avg latency (ms)", f"{cand['avg_latency_ms']:.2f}",
          None if not base else f"{cand['avg_latency_ms'] - base['avg_latency_ms']:+.2f}", delta_color="inverse")

if base:
    st.caption(f"Baseline: run {base['run_id']} ({base['version']}). Minimum allowed score shown as 'threshold'.")
    df = pd.DataFrame(compare(base, cand))
    df["threshold"] = df["metric"].map(thresholds["min_scores"])
    st.dataframe(df.round(3), hide_index=True, use_container_width=True)
    chart = df[df.metric != "avg_latency_ms"].set_index("metric")[["baseline", "candidate"]]
    st.bar_chart(chart, stack=False)

# --- Per-question details -------------------------------------------------------
st.header("Per-question results")
cases = pd.DataFrame(storage.case_rows(conn, cand["run_id"]))
st.dataframe(cases.round(3), hide_index=True, use_container_width=True)
