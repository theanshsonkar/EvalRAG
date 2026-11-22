"""Runs a dataset through the RAG app, scores every case, and stores the run."""
import json
import subprocess
import time
from datetime import datetime, timezone

from . import storage
from .metrics import score_case
from .rag_app import ROOT, RAGApp


def load_dataset(path):
    data = json.loads((ROOT / path).read_text())
    if not data.get("cases"):
        raise ValueError("dataset has no cases")
    for c in data["cases"]:
        missing = {"id", "question", "reference", "source"} - c.keys()
        if missing:
            raise ValueError(f"case {c.get('id', '?')} is missing {sorted(missing)}")
    return data


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return None


def run_evaluation(config, dataset_path="data/dataset.json", conn=None, progress=print):
    dataset = load_dataset(dataset_path)
    app = RAGApp(config)
    results = []
    cases = dataset["cases"]
    for i, case in enumerate(cases, 1):
        start = time.perf_counter()
        try:
            out = app.answer(case["question"])
            latency = (time.perf_counter() - start) * 1000
            results.append({"case_id": case["id"], "question": case["question"],
                            "answer": out["answer"], "contexts": out["contexts"],
                            "latency_ms": latency,
                            "scores": score_case(case, out["answer"], out["contexts"])})
        except Exception as e:  # record the failure and keep going (NFR2)
            results.append({"case_id": case["id"], "question": case["question"],
                            "latency_ms": (time.perf_counter() - start) * 1000, "error": str(e)})
        progress(f"  [{i}/{len(cases)}] {case['id']} done")
    run = {"version": config["version"], "dataset": dataset["name"], "config": config,
           "git_commit": git_commit(), "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "status": "completed_with_errors" if any("error" in r for r in results) else "completed"}
    conn = conn or storage.connect()
    return storage.save_run(conn, run, results)
