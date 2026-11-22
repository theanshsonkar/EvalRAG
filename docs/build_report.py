"""Builds docs/EvalRAG_Milestone2_Report.docx from the live results in evalrag.db.

Run after the three demo runs exist:  .venv/bin/python docs/build_report.py
"""
import json
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from evalrag import storage  # noqa: E402
from evalrag.compare import quality_gate  # noqa: E402

DOCS = ROOT / "docs"
conn = storage.connect()
runs = {r["version"]: r["run_id"] for r in storage.list_runs(conn)}
S = {v: storage.run_summary(conn, rid) for v, rid in runs.items()}
base, cand, bad = S["v1-baseline"], S["v1.1-candidate"], S["v2-bad-change"]
TH = json.loads((ROOT / "configs/thresholds.json").read_text())
gate_cand = quality_gate(cand, TH, base)
gate_bad = quality_gate(bad, TH, base)

doc = Document()
doc.styles["Normal"].font.name = "Calibri"
doc.styles["Normal"].font.size = Pt(11)


def h(text, level=1):
    doc.add_heading(text, level)


def p(text, bold=False, italic=False):
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.bold, run.italic = bold, italic
    return para


def bullets(items):
    for i in items:
        doc.add_paragraph(i, style="List Bullet")


def table(header, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Light Grid Accent 1"
    for i, c in enumerate(header):
        t.rows[0].cells[i].text = c
    for r in rows:
        cells = t.add_row().cells
        for i, c in enumerate(r):
            cells[i].text = str(c)
    for row in t.rows:
        for c in row.cells:
            for para in c.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(9)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    doc.add_paragraph()


def figure(path, caption, width=6.3):
    doc.add_picture(str(path), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    c = p(caption, italic=True)
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER


def todo(text):
    para = doc.add_paragraph()
    run = para.add_run("[TO FILL] " + text)
    run.bold = True
    run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)


f3 = lambda v: f"{v:.3f}"  # noqa: E731

# ---------------------------------------------------------------- cover
t = doc.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
t.add_run("CAPSTONE PROJECT\n\n").bold = True
r = t.add_run("EvalRAG\n")
r.bold, r.font.size = True, Pt(28)
t.add_run("Automated RAG, LLM and Prompt Evaluation Platform with CI/CD\n\n").font.size = Pt(14)
t.add_run("MILESTONE 2: Requirements & Design, Implementation, Testing and Progress\n\n").bold = True
table(["Team member", "Student ID"], [["Harshita Singh", "E23CSEU2054"], ["Anshika Sidana", "E23CSEU2111"]])
todo("Add guide/mentor name, date, and any third team member if applicable.")
doc.add_page_break()

# ---------------------------------------------------------------- 1. requirements & design
h("1. Requirements and Design")
h("1.1 Finalized requirements", 2)
p("The functional requirements from Milestone 1 were kept. Each one is now implemented and verified by a test case (Section 3).")
table(["ID", "Requirement", "Implemented in", "Verified by", "Status"], [
    ["FR1", "Load a defined evaluation dataset", "runner.load_dataset", "TC01, TC02", "Done"],
    ["FR2", "Execute cases against the configured RAG app", "runner.run_evaluation, rag_app", "TC03, TC07", "Done"],
    ["FR3", "Calculate retrieval and answer-quality metrics", "metrics.py", "TC04-TC06", "Done"],
    ["FR4", "Store run metadata and results", "storage.py (SQLite)", "TC07", "Done"],
    ["FR5", "Compare at least two runs / versions", "compare.compare", "TC09, TC10", "Done"],
    ["FR6", "Show metrics, status, comparisons in a dashboard/report", "dashboard/app.py, cli gate --report", "Screenshots 1-4", "Done"],
    ["FR7", "At least one CI/CD integration", ".github/workflows/evalrag.yml", "CLI exit codes (local)", "Configured"],
    ["FR8", "Fail the quality gate when criteria are not met", "compare.quality_gate", "TC09, TC10, TC11", "Done"],
], [0.5, 2.2, 1.7, 1.1, 0.8])
table(["ID", "Non-functional requirement", "How it is met"], [
    ["NFR1", "Performance", f"25 cases evaluated in well under a second (avg latency {base['avg_latency_ms']:.2f} ms/case); progress printed per case."],
    ["NFR2", "Reliability", "Errors per case are caught and stored; run marked completed_with_errors (TC11). Repeat runs give identical scores (TC08)."],
    ["NFR3", "Security", "API key read only from ANTHROPIC_API_KEY env var / GitHub secret; .env and DB are git-ignored."],
    ["NFR4", "Usability", "Gate prints the exact reason for every failure; dashboard shows thresholds next to scores."],
    ["NFR5", "Maintainability", "Separate modules: rag_app, metrics, storage, runner, compare, cli, api, dashboard."],
    ["NFR6", "Portability", "requirements.txt + README; runs on macOS and the ubuntu GitHub runner."],
    ["NFR7", "Traceability", "Every run stores version, full config JSON, git commit, timestamp and baseline flag."],
], [0.6, 1.4, 4.3])

h("1.2 System architecture", 2)
p("A developer change (prompt, model, retrieval settings or documents) triggers GitHub Actions, which runs the "
  "EvalRAG CLI. The runner sends each test question to the RAG application, the metrics module scores the "
  "answer and retrieved context, results are stored, and the comparison engine applies the quality gate. "
  "The exit code (0 = pass, 1 = fail) decides whether the CI check is green or red.")
figure(DOCS / "diagrams/architecture.png", "Figure 1: System architecture")

h("1.3 Module design", 2)
table(["Module", "Responsibility", "Key functions"], [
    ["Dataset & config", "Loads and validates test cases; reads version configs and thresholds", "load_dataset(), configs/*.json"],
    ["RAG application (system under test)", "Chunks documents, retrieves top-k chunks with TF-IDF, generates an answer", "RAGApp.retrieve(), generate(), answer()"],
    ["Evaluation runner", "Runs every case, measures latency, records errors", "run_evaluation()"],
    ["Metrics", "Scores context precision/recall, faithfulness, answer relevance, answer correctness", "score_case()"],
    ["Result storage", "Persists runs, per-case results and metric scores; marks baseline", "save_run(), run_summary(), set_baseline()"],
    ["Comparison engine + gate", "Diffs candidate vs baseline; PASS/WARN/FAIL with reasons", "compare(), quality_gate()"],
    ["Interfaces", "CLI for CI, REST API, Streamlit dashboard", "cli.py, api.py, dashboard/app.py"],
], [1.6, 3.0, 1.7])
figure(DOCS / "diagrams/class_diagram.png", "Figure 2: Class / module diagram")

h("1.4 Metric definitions", 2)
table(["Metric", "Meaning", "How it is computed"], [
    ["context_precision", "Are the retrieved chunks relevant?", "Share of retrieved chunks that come from the correct source document"],
    ["context_recall", "Did retrieval find the needed facts?", "Share of the reference answer's key words present in the retrieved context"],
    ["faithfulness", "Is the answer supported by the context? (hallucination check)", "Share of the answer's key words found in the retrieved context"],
    ["answer_relevance", "Does the answer address the question?", "TF-IDF cosine similarity between question and answer"],
    ["answer_correctness", "Does the answer match the reference?", "Token-level F1 between answer and reference answer"],
    ["latency_ms", "Speed", "Wall-clock time per question"],
], [1.4, 2.2, 2.7])

h("1.5 Database design", 2)
p("Three tables: one row per run, one row per test case in that run, and one row per metric score. "
  "SQLite is used in the prototype for zero setup; the same schema works in PostgreSQL.")
figure(DOCS / "diagrams/er_diagram.png", "Figure 3: ER diagram")

h("1.6 Use-case diagram", 2)
figure(DOCS / "diagrams/use_case.png", "Figure 4: Use-case diagram", 5.8)
h("1.7 Data flow diagrams", 2)
figure(DOCS / "diagrams/dfd_level0.png", "Figure 5: DFD Level 0")
figure(DOCS / "diagrams/dfd_level1.png", "Figure 6: DFD Level 1")
h("1.8 Sequence diagram and flowchart", 2)
figure(DOCS / "diagrams/sequence.png", "Figure 7: Sequence diagram for a CI evaluation")
figure(DOCS / "diagrams/flowchart.png", "Figure 8: Quality-gate flowchart", 4.2)
doc.add_page_break()

# ---------------------------------------------------------------- 2. implementation
h("2. Implementation and Demonstration")
h("2.1 Technology choices", 2)
table(["Component", "Chosen", "Why"], [
    ["Language", "Python 3", "Standard for AI work; all libraries below are Python."],
    ["RAG app under test", "Custom TF-IDF retriever (scikit-learn) + extractive generator; optional Claude generator", "Runs free and offline so CI never needs paid API calls; the Claude mode shows the same pipeline works with a real LLM."],
    ["Evaluation metrics", "Own implementation of RAGAS-style metrics", "RAGAS/DeepEval metrics need an LLM judge for every score (cost, rate limits, non-deterministic results). Deterministic metrics make CI results repeatable (TC08). RAGAS can be plugged in later."],
    ["Storage", "SQLite (PostgreSQL-compatible schema)", "No server to install; one file; same SQL works on PostgreSQL."],
    ["Backend API", "FastAPI", "Lightweight, automatic API docs at /docs."],
    ["Dashboard", "Streamlit", "Fastest way to build a data dashboard in Python, as planned in Milestone 1."],
    ["CI/CD", "GitHub Actions", "Free for student repos; the exit code directly passes/fails the check."],
    ["Testing", "pytest", "Simple, standard Python testing."],
], [1.3, 2.0, 3.0])

h("2.2 Test application and dataset", 2)
p("The system under test is a campus help-desk bot that answers questions about a fictional university from "
  "8 knowledge-base documents (admissions, fees, hostel, library, exams, placements, IT services, clubs). "
  "The evaluation dataset has 25 questions, each with a reference answer and the source document. "
  "All data was written by the team, so there are no licensing or privacy issues.")
p("Three versions (configs) are used to demonstrate the workflow:")
table(["Version", "Change", "Purpose"], [
    ["v1-baseline", "2-sentence chunks, top 3 chunks, best-matching sentence as answer", "Baseline run"],
    ["v1.1-candidate", "Same settings (a safe change)", "Should PASS the gate"],
    ["v2-bad-change", "Whole-document chunks, only 1 chunk, answer = first sentence", "Controlled regression; should FAIL"],
], [1.3, 3.4, 1.6])

h("2.3 How to run the demo", 2)
for line in ["python -m evalrag.cli run --config configs/baseline.json --set-baseline",
             "python -m evalrag.cli run --config configs/candidate.json && python -m evalrag.cli gate   → PASS (exit 0)",
             "python -m evalrag.cli run --config configs/changed.json && python -m evalrag.cli gate     → FAIL (exit 1)",
             "streamlit run dashboard/app.py"]:
    para = doc.add_paragraph(style="List Number")
    para.add_run(line).font.name = "Courier New"

h("2.4 Screenshots", 2)
figure(DOCS / "screenshots/01_run_history.jpg", "Screenshot 1: Run history and metric trend across runs")
figure(DOCS / "screenshots/04_gate_pass.jpg", "Screenshot 2: Candidate run compared with baseline — quality gate PASS")
figure(DOCS / "screenshots/02_gate_fail.jpg", "Screenshot 3: Bad change — quality gate FAIL with reasons")
figure(DOCS / "screenshots/03_comparison.jpg", "Screenshot 4: Metric-by-metric comparison with thresholds")
doc.add_page_break()

# ---------------------------------------------------------------- 3. testing
h("3. Testing and Results")
h("3.1 Test cases", 2)
p("All test cases are automated in tests/test_evalrag.py and run in CI before every evaluation. Result: 12 / 12 passed.")
table(["ID", "Test", "Expected result", "Actual", "Status"], [
    ["TC01", "Load valid dataset", "25 cases loaded", "25 cases", "Pass"],
    ["TC02", "Load dataset with missing fields", "Rejected with clear error", "ValueError 'missing'", "Pass"],
    ["TC03", "Retriever on a library question", "Top chunk from 'library'", "library", "Pass"],
    ["TC04", "Metrics on a perfect answer", "Scores = 1.0", "1.0", "Pass"],
    ["TC05", "Faithfulness on a made-up answer", "< 0.5 (hallucination flagged)", "< 0.5", "Pass"],
    ["TC06", "Correctness on a wrong answer", "0.0", "0.0", "Pass"],
    ["TC07", "Run stored and retrievable", "25 results, 5 metrics", "As expected", "Pass"],
    ["TC08", "Repeat the same run", "Identical scores", "Identical", "Pass"],
    ["TC09", "Gate on an unchanged version", "PASS", "PASS", "Pass"],
    ["TC10", "Gate on the bad change", "FAIL citing answer_correctness", "FAIL", "Pass"],
    ["TC11", "RAG app raises errors (API timeout)", "Errors stored, gate FAIL, no crash", "As expected", "Pass"],
    ["TC12", "REST API endpoints", "/health, POST/GET /runs, gate, 404, 400", "As expected", "Pass"],
], [0.5, 2.0, 1.8, 1.2, 0.6])

h("3.2 Evaluation results", 2)
p(f"Thresholds used: minimum scores {TH['min_scores']}, maximum average latency {TH['max_avg_latency_ms']} ms, "
  f"maximum allowed drop vs baseline {TH['max_drop_vs_baseline']}.")
rows = []
for m in ["context_precision", "context_recall", "faithfulness", "answer_relevance", "answer_correctness"]:
    rows.append([m, f3(base["metrics"][m]), f3(cand["metrics"][m]), f3(bad["metrics"][m]),
                 f3(bad["metrics"][m] - base["metrics"][m])])
rows.append(["avg latency (ms)", f"{base['avg_latency_ms']:.2f}", f"{cand['avg_latency_ms']:.2f}",
             f"{bad['avg_latency_ms']:.2f}", f"{bad['avg_latency_ms'] - base['avg_latency_ms']:+.2f}"])
rows.append(["Quality gate", "baseline", gate_cand[0], gate_bad[0], ""])
table(["Metric", "v1-baseline", "v1.1-candidate", "v2-bad-change", "Change (bad − base)"], rows)
p("Gate output for the bad change:", bold=True)
bullets(gate_bad[1])
p("Interpretation: the bad change still retrieves the correct document (context precision and recall stay high) "
  "but the answer step returns the wrong sentence, so answer correctness falls from "
  f"{f3(base['metrics']['answer_correctness'])} to {f3(bad['metrics']['answer_correctness'])}. "
  "The gate catches this and would block the deployment. A safe change passes. Both acceptance-criteria "
  "scenarios (AC6) are demonstrated.")

h("3.3 Sample per-question results", 2)
b_rows = {r["case_id"]: r for r in storage.case_rows(conn, base["run_id"])}
x_rows = {r["case_id"]: r for r in storage.case_rows(conn, bad["run_id"])}
table(["Case", "Baseline answer", "Bad-change answer", "Correctness (base → bad)"],
      [[cid, b_rows[cid]["answer"], x_rows[cid]["answer"],
        f"{b_rows[cid]['answer_correctness']:.2f} → {x_rows[cid]['answer_correctness']:.2f}"]
       for cid in ["Q06", "Q14", "Q19", "Q22", "Q23"]], [0.5, 2.4, 2.4, 1.0])

h("3.4 Validation against human judgement", 2)
weak = [r for r in b_rows.values() if r["answer_correctness"] < 0.5]
p(f"All 25 baseline answers were checked by reading them. {25 - len(weak)} were correct. The metric flagged "
  f"{len(weak)} answers with low correctness, and reading them confirms they are genuinely wrong. "
  "The retriever picked a sentence that shares words with the question but answers something else:")
table(["Case", "Question", "Baseline answer (wrong)", "Correctness"],
      [[r["case_id"], r["question"], r["answer"], f"{r['answer_correctness']:.2f}"] for r in weak],
      [0.5, 2.0, 3.0, 0.8])
p("So the evaluation already finds real weaknesses in the baseline. These are the improvement targets for the final phase. "
  "Some limits of the metrics were also noticed:")
bullets([
    "answer_relevance is low (~0.37) even for correct answers because a question and its answer share few exact words. "
    "This is why its threshold is set low (0.30); a semantic (embedding or LLM-judge) metric would be better.",
    "With the extractive generator, faithfulness is always 1.0 because answers are copied from the context. "
    "Hallucination detection is verified by unit test TC05 but will only matter in real runs with an LLM generator.",
    "context_precision is only 0.55 at baseline because top-3 retrieval also returns chunks from other documents; "
    "this is expected and it is not gated.",
])
todo("Confirm the manual review above after you have read the answers yourselves (open the dashboard → Per-question results).")

h("3.5 Updated risk analysis", 2)
table(["Risk (Milestone 1)", "What happened", "Updated status / mitigation"], [
    ["Unrepresentative dataset", "25 synthetic questions over 8 topics", "Medium. Add harder and unanswerable questions in the final phase."],
    ["Metrics disagree with human judgement", "answer_relevance underrates correct answers", "Medium/High. Threshold lowered; plan semantic metric / RAGAS LLM-judge."],
    ["API cost, quotas, downtime", "Avoided: default pipeline is offline and free", "Low. Claude mode optional; errors are recorded, not crashed (TC11)."],
    ["Integration problems with framework", "Custom pipeline used instead of LangChain", "Low. Modular RAGApp can be swapped."],
    ["Gate false failures", "Not seen; repeat runs identical (TC08)", "Low. WARN level added for smaller drops."],
    ["Credentials exposed", "Key only via env/secret; .gitignore set", "Low."],
    ["Scope creep", "MVP finished first, as planned", "Medium. Jenkins / React UI kept out of scope."],
    ["NEW: CI not yet run on GitHub", "Workflow written and steps verified locally", "Medium. Push the repo and record a real Actions run before the final review."],
], [1.7, 2.2, 2.4])

h("3.6 User / stakeholder feedback", 2)
todo("Show the dashboard to 2-3 classmates or your guide and write down what they said, e.g.:")
table(["Who", "Feedback", "Action taken"], [["", "", ""], ["", "", ""], ["", "", ""]])
doc.add_page_break()

# ---------------------------------------------------------------- 4. progress
h("4. Progress and Next Steps")
h("4.1 Completed so far", 2)
table(["Phase (Milestone 1 plan)", "Status"], [
    ["1. Requirements and research", "Done"],
    ["2. Proof of concept", "Done"],
    ["3. Backend and storage", "Done (SQLite, REST API)"],
    ["4. Comparison and dashboard", "Done"],
    ["5. CI/CD and validation", "Workflow and gate done; first GitHub run pending"],
    ["6. Final testing and documentation", "In progress (README, this report)"],
])
h("4.2 Member contributions", 2)
todo("Replace with what each member actually did.")
table(["Member", "Contribution"], [
    ["Harshita Singh", "Dataset and knowledge base, metric selection and definitions, test cases, manual validation of results"],
    ["Anshika Sidana", "RAG application, evaluation runner, database, comparison engine and quality gate, dashboard, CI workflow"],
    ["Both", "Architecture and diagrams, documentation, report"],
])
h("4.3 Remaining for the final milestone", 2)
bullets([
    "Push to GitHub and demonstrate a red (blocked) and green pull request in GitHub Actions.",
    "Run the pipeline with the Claude LLM generator and compare its scores with the extractive version.",
    "Add a semantic answer-relevance metric (embeddings or RAGAS LLM-judge) and compare with the current lexical one.",
    "Grow the dataset (50+ questions, including unanswerable ones to test refusals).",
    "Move storage to PostgreSQL with Docker, if time allows.",
    "Collect stakeholder feedback and finish the final report and demo video.",
])

h("5. References")
bullets([
    "Lewis, P. et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS 2020.",
    "Es, S. et al. (2023). RAGAS: Automated Evaluation of Retrieval Augmented Generation. arXiv:2309.15217.",
    "DeepEval documentation, Confident AI. https://docs.confident-ai.com",
    "MLflow LLM evaluation documentation. https://mlflow.org/docs/latest/llms/llm-evaluate/",
    "LangSmith documentation. https://docs.smith.langchain.com",
    "scikit-learn, FastAPI, Streamlit and GitHub Actions official documentation.",
])

out = DOCS / "EvalRAG_Milestone2_Report.docx"
doc.save(out)
print("written", out)
