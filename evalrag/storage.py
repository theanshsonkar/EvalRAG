"""Result storage in SQLite (file: evalrag.db). Schema mirrors the ER diagram.

SQLite keeps the prototype zero-setup; the same tables can be created in
PostgreSQL for a shared deployment.
"""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "evalrag.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    version       TEXT NOT NULL,
    dataset       TEXT NOT NULL,
    config_json   TEXT NOT NULL,
    git_commit    TEXT,
    started_at    TEXT NOT NULL,
    status        TEXT NOT NULL,
    is_baseline   INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS case_results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        INTEGER NOT NULL REFERENCES runs(run_id),
    case_id       TEXT NOT NULL,
    question      TEXT NOT NULL,
    answer        TEXT,
    contexts_json TEXT,
    latency_ms    REAL,
    error         TEXT
);
CREATE TABLE IF NOT EXISTS metric_scores (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id     INTEGER NOT NULL REFERENCES case_results(id),
    metric        TEXT NOT NULL,
    score         REAL NOT NULL
);
"""


def connect(db_path=None):
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save_run(conn, run, results):
    cur = conn.execute(
        "INSERT INTO runs (version, dataset, config_json, git_commit, started_at, status) VALUES (?,?,?,?,?,?)",
        (run["version"], run["dataset"], json.dumps(run["config"]), run.get("git_commit"),
         run["started_at"], run["status"]))
    run_id = cur.lastrowid
    for r in results:
        rid = conn.execute(
            "INSERT INTO case_results (run_id, case_id, question, answer, contexts_json, latency_ms, error) VALUES (?,?,?,?,?,?,?)",
            (run_id, r["case_id"], r["question"], r.get("answer"), json.dumps(r.get("contexts", [])),
             r.get("latency_ms"), r.get("error"))).lastrowid
        conn.executemany("INSERT INTO metric_scores (result_id, metric, score) VALUES (?,?,?)",
                         [(rid, m, s) for m, s in r.get("scores", {}).items()])
    conn.commit()
    return run_id


def set_baseline(conn, run_id):
    conn.execute("UPDATE runs SET is_baseline = 0")
    conn.execute("UPDATE runs SET is_baseline = 1 WHERE run_id = ?", (run_id,))
    conn.commit()


def get_baseline_id(conn):
    row = conn.execute("SELECT run_id FROM runs WHERE is_baseline = 1").fetchone()
    return row["run_id"] if row else None


def list_runs(conn):
    return [dict(r) for r in conn.execute(
        "SELECT run_id, version, dataset, git_commit, started_at, status, is_baseline FROM runs ORDER BY run_id DESC")]


def run_summary(conn, run_id):
    """Average of every metric plus latency and error count for one run."""
    run = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if run is None:
        return None
    metrics = {r["metric"]: r["avg"] for r in conn.execute(
        """SELECT m.metric, AVG(m.score) AS avg FROM metric_scores m
           JOIN case_results c ON c.id = m.result_id WHERE c.run_id = ? GROUP BY m.metric""", (run_id,))}
    stats = conn.execute(
        "SELECT COUNT(*) AS n, AVG(latency_ms) AS lat, SUM(error IS NOT NULL) AS errors FROM case_results WHERE run_id = ?",
        (run_id,)).fetchone()
    return {"run_id": run_id, "version": run["version"], "started_at": run["started_at"],
            "status": run["status"], "is_baseline": bool(run["is_baseline"]),
            "num_cases": stats["n"], "errors": stats["errors"] or 0,
            "avg_latency_ms": stats["lat"], "metrics": metrics}


def case_rows(conn, run_id):
    rows = conn.execute(
        "SELECT id, case_id, question, answer, latency_ms, error FROM case_results WHERE run_id = ? ORDER BY case_id",
        (run_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        for m in conn.execute("SELECT metric, score FROM metric_scores WHERE result_id = ?", (r["id"],)):
            d[m["metric"]] = m["score"]
        del d["id"]
        out.append(d)
    return out
