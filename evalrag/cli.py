"""Command line interface.

  python -m evalrag.cli run --config configs/baseline.json [--set-baseline]
  python -m evalrag.cli compare [--run RUN_ID]
  python -m evalrag.cli gate [--run RUN_ID] [--thresholds configs/thresholds.json] [--report report.md]
  python -m evalrag.cli list
"""
import argparse
import json
import sys

from . import storage
from .compare import compare, quality_gate
from .rag_app import ROOT
from .runner import run_evaluation


def fmt(v):
    return "-" if v is None else f"{v:.3f}"


def latest_run_id(conn):
    runs = storage.list_runs(conn)
    if not runs:
        sys.exit("No runs stored yet. Run `python -m evalrag.cli run` first.")
    return runs[0]["run_id"]


def report_markdown(cand, base, rows, status, reasons):
    lines = [f"# EvalRAG report: run {cand['run_id']} ({cand['version']})", "",
             f"**Quality gate: {status}**", ""] + [f"- {r}" for r in reasons] + ["",
             f"Cases: {cand['num_cases']}, errors: {cand['errors']}, avg latency: {cand['avg_latency_ms']:.1f} ms", ""]
    if base:
        lines += [f"Compared with baseline run {base['run_id']} ({base['version']}):", "",
                  "| Metric | Baseline | Candidate | Change |", "|---|---|---|---|"]
        lines += [f"| {r['metric']} | {fmt(r['baseline'])} | {fmt(r['candidate'])} | {fmt(r['change'])} |" for r in rows]
    return "\n".join(lines) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(prog="evalrag")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="evaluate a configuration and store the run")
    r.add_argument("--config", default="configs/baseline.json")
    r.add_argument("--dataset", default="data/dataset.json")
    r.add_argument("--set-baseline", action="store_true")
    for name in ("compare", "gate"):
        s = sub.add_parser(name)
        s.add_argument("--run", type=int, help="candidate run id (default: latest)")
        s.add_argument("--thresholds", default="configs/thresholds.json")
        s.add_argument("--report", help="write a markdown report to this file")
    sub.add_parser("list")
    args = p.parse_args(argv)
    conn = storage.connect()

    if args.cmd == "run":
        config = json.loads((ROOT / args.config).read_text())
        print(f"Evaluating {config['version']} on {args.dataset}")
        run_id = run_evaluation(config, args.dataset, conn)
        if args.set_baseline:
            storage.set_baseline(conn, run_id)
        s = storage.run_summary(conn, run_id)
        print(f"Run {run_id} stored ({s['status']}). Avg latency {s['avg_latency_ms']:.1f} ms")
        for m, v in s["metrics"].items():
            print(f"  {m:20s} {v:.3f}")
        return 0

    if args.cmd == "list":
        for run in storage.list_runs(conn):
            print(f"{run['run_id']:>4}  {run['version']:20s} {run['started_at']}  {run['status']}"
                  + ("  [baseline]" if run["is_baseline"] else ""))
        return 0

    cand = storage.run_summary(conn, args.run or latest_run_id(conn))
    if cand is None:
        sys.exit(f"Run {args.run} not found")
    base_id = storage.get_baseline_id(conn)
    base = storage.run_summary(conn, base_id) if base_id else None
    rows = compare(base, cand) if base else []
    thresholds = json.loads((ROOT / args.thresholds).read_text())
    status, reasons = quality_gate(cand, thresholds, base)
    report = report_markdown(cand, base, rows, status, reasons)
    print(report)
    if args.report:
        (ROOT / args.report).write_text(report)
    if args.cmd == "gate" and status == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
