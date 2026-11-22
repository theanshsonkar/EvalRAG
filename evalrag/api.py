"""REST API (FastAPI). Start with: uvicorn evalrag.api:app --reload"""
import json

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import storage
from .compare import compare, quality_gate
from .rag_app import ROOT
from .runner import run_evaluation

app = FastAPI(title="EvalRAG API")


class RunRequest(BaseModel):
    config_path: str = "configs/baseline.json"
    dataset_path: str = "data/dataset.json"
    set_baseline: bool = False


def _summary(conn, run_id):
    s = storage.run_summary(conn, run_id)
    if s is None:
        raise HTTPException(404, f"run {run_id} not found")
    return s


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/runs")
def list_runs():
    return storage.list_runs(storage.connect())


@app.post("/runs")
def create_run(req: RunRequest):
    conn = storage.connect()
    try:
        config = json.loads((ROOT / req.config_path).read_text())
        run_id = run_evaluation(config, req.dataset_path, conn, progress=lambda _: None)
    except (FileNotFoundError, ValueError, KeyError) as e:
        raise HTTPException(400, str(e))
    if req.set_baseline:
        storage.set_baseline(conn, run_id)
    return _summary(conn, run_id)


@app.get("/runs/{run_id}")
def get_run(run_id: int):
    conn = storage.connect()
    return {**_summary(conn, run_id), "cases": storage.case_rows(conn, run_id)}


@app.post("/runs/{run_id}/baseline")
def make_baseline(run_id: int):
    conn = storage.connect()
    _summary(conn, run_id)
    storage.set_baseline(conn, run_id)
    return {"baseline": run_id}


@app.get("/runs/{run_id}/gate")
def gate(run_id: int, thresholds_path: str = "configs/thresholds.json"):
    conn = storage.connect()
    cand = _summary(conn, run_id)
    base_id = storage.get_baseline_id(conn)
    base = storage.run_summary(conn, base_id) if base_id else None
    status, reasons = quality_gate(cand, json.loads((ROOT / thresholds_path).read_text()), base)
    return {"run_id": run_id, "status": status, "reasons": reasons,
            "comparison": compare(base, cand) if base else []}
