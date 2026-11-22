# EvalRAG: Automated RAG / LLM evaluation with a CI/CD quality gate

EvalRAG runs a fixed test set through a RAG application, scores every answer,
stores the run, compares it with a baseline, and fails the CI build when quality drops.

## Setup
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run an evaluation
```bash
.venv/bin/python -m evalrag.cli run --config configs/baseline.json --set-baseline   # baseline run
.venv/bin/python -m evalrag.cli run --config configs/candidate.json                 # a new version
.venv/bin/python -m evalrag.cli gate                                                # PASS -> exit 0, FAIL -> exit 1
.venv/bin/python -m evalrag.cli run --config configs/changed.json                   # deliberately bad change
.venv/bin/python -m evalrag.cli gate --report eval_report.md                        # FAIL, writes a report
.venv/bin/python -m evalrag.cli list                                                # run history
```

## Dashboard and API
```bash
.venv/bin/streamlit run dashboard/app.py      # http://localhost:8501
.venv/bin/uvicorn evalrag.api:app --reload    # http://localhost:8000/docs
```

## Tests
```bash
.venv/bin/python -m pytest -v
```

## CI/CD
`.github/workflows/evalrag.yml` runs on every push and pull request: unit tests, baseline run,
candidate run (`configs/candidate.json`), then the quality gate. A FAIL makes the job red,
which blocks the merge when branch protection is on. The markdown report is shown in the job summary.

## Project layout
| Path | What it is |
|---|---|
| `data/kb/` | Knowledge base (8 documents about a fictional university) |
| `data/dataset.json` | 25 test questions with reference answers and source document |
| `configs/` | RAG app versions (`baseline`, `candidate`, `changed`) and `thresholds.json` |
| `evalrag/rag_app.py` | RAG application under test (TF-IDF retriever + extractive or Claude generator) |
| `evalrag/metrics.py` | context precision/recall, faithfulness, answer relevance, answer correctness |
| `evalrag/storage.py` | SQLite storage (`runs`, `case_results`, `metric_scores`) |
| `evalrag/compare.py` | baseline comparison and quality gate |
| `evalrag/cli.py`, `evalrag/api.py`, `dashboard/app.py` | CLI, REST API, Streamlit dashboard |
| `docs/` | diagrams, screenshots and the Milestone 2 report |

## Configuration
* `chunk_size`, `top_k`: retrieval settings.
* `generator`: `extractive` (free, offline, default) or `claude` (needs `ANTHROPIC_API_KEY` as an
  environment variable or GitHub secret; never commit keys).
* `configs/thresholds.json`: minimum score per metric, max average latency, and the largest
  allowed drop from the baseline.

## Limitations
* Metrics are lightweight lexical versions of RAGAS-style metrics, chosen so CI is free and
  repeatable. They measure word overlap, not meaning, and can disagree with human judgement.
* With the extractive generator, answers are copied from the context, so faithfulness is always 1.0.
  Hallucination detection only becomes meaningful with an LLM generator.
* The dataset is small (25 questions) and synthetic.
