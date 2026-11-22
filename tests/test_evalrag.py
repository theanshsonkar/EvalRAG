"""Test cases TC01-TC12 (listed in the Milestone 2 report)."""
import json

import pytest
from fastapi.testclient import TestClient

from evalrag import api, metrics, storage
from evalrag.compare import quality_gate
from evalrag.rag_app import ROOT, RAGApp
from evalrag.runner import load_dataset, run_evaluation

BASELINE = json.loads((ROOT / "configs/baseline.json").read_text())
CHANGED = json.loads((ROOT / "configs/changed.json").read_text())
THRESHOLDS = json.loads((ROOT / "configs/thresholds.json").read_text())


@pytest.fixture
def conn(tmp_path):
    return storage.connect(tmp_path / "test.db")


def test_tc01_valid_dataset_loads():
    assert len(load_dataset("data/dataset.json")["cases"]) == 25


def test_tc02_invalid_dataset_rejected(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"name": "bad", "cases": [{"id": "X", "question": "q"}]}))
    with pytest.raises(ValueError, match="missing"):
        load_dataset(bad)


def test_tc03_retriever_finds_correct_source():
    ctx = RAGApp(BASELINE).retrieve("What is the fine for an overdue library book?")
    assert ctx[0]["source"] == "library"


def test_tc04_metrics_perfect_answer():
    ctx = [{"source": "library", "text": "A fine of 5 rupees per day is charged for each overdue book."}]
    ref = ctx[0]["text"]
    assert metrics.faithfulness(ref, ctx) == 1.0
    assert metrics.answer_correctness(ref, ref) == pytest.approx(1.0)
    assert metrics.context_precision(ctx, "library") == 1.0


def test_tc05_faithfulness_detects_hallucination():
    ctx = [{"source": "library", "text": "The library is open from 8 AM to 11 PM."}]
    assert metrics.faithfulness("The library is open 24 hours with free coffee.", ctx) < 0.5


def test_tc06_wrong_answer_scores_low():
    assert metrics.answer_correctness("Hostel gates close at 10 PM.", "The fee is 1500 rupees.") == 0.0


def test_tc07_run_is_stored_and_retrievable(conn):
    run_id = run_evaluation(BASELINE, conn=conn, progress=lambda _: None)
    s = storage.run_summary(conn, run_id)
    assert s["num_cases"] == 25 and s["errors"] == 0
    assert set(s["metrics"]) == set(metrics.METRIC_NAMES)
    assert len(storage.case_rows(conn, run_id)) == 25


def test_tc08_repeat_runs_are_identical(conn):
    a = run_evaluation(BASELINE, conn=conn, progress=lambda _: None)
    b = run_evaluation(BASELINE, conn=conn, progress=lambda _: None)
    assert storage.run_summary(conn, a)["metrics"] == storage.run_summary(conn, b)["metrics"]


def test_tc09_gate_passes_good_version(conn):
    base = run_evaluation(BASELINE, conn=conn, progress=lambda _: None)
    storage.set_baseline(conn, base)
    cand = run_evaluation(BASELINE, conn=conn, progress=lambda _: None)
    status, _ = quality_gate(storage.run_summary(conn, cand), THRESHOLDS, storage.run_summary(conn, base))
    assert status == "PASS"


def test_tc10_gate_fails_regressed_version(conn):
    base = run_evaluation(BASELINE, conn=conn, progress=lambda _: None)
    cand = run_evaluation(CHANGED, conn=conn, progress=lambda _: None)
    status, reasons = quality_gate(storage.run_summary(conn, cand), THRESHOLDS, storage.run_summary(conn, base))
    assert status == "FAIL"
    assert any("answer_correctness" in r for r in reasons)


def test_tc11_errors_are_recorded_not_crashing(conn, monkeypatch):
    def boom(self, q):
        raise RuntimeError("LLM API timeout")
    monkeypatch.setattr(RAGApp, "answer", boom)
    run_id = run_evaluation(BASELINE, conn=conn, progress=lambda _: None)
    s = storage.run_summary(conn, run_id)
    assert s["status"] == "completed_with_errors" and s["errors"] == 25
    assert quality_gate(s, THRESHOLDS)[0] == "FAIL"


def test_tc12_api_endpoints(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "api.db")
    client = TestClient(api.app)
    assert client.get("/health").json() == {"status": "ok"}
    run = client.post("/runs", json={"set_baseline": True}).json()
    assert run["is_baseline"] and run["num_cases"] == 25
    assert client.get(f"/runs/{run['run_id']}/gate").json()["status"] == "PASS"
    assert client.get("/runs/999").status_code == 404
    assert client.post("/runs", json={"config_path": "configs/nope.json"}).status_code == 400
