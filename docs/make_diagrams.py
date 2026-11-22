"""Draws the design diagrams for the Milestone 2 report into docs/diagrams/.

Run: .venv/bin/python docs/make_diagrams.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Ellipse, FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parent / "diagrams"
OUT.mkdir(exist_ok=True)
BLUE, GREEN, ORANGE, GREY = "#dbe8f7", "#dff2e1", "#fde9d2", "#eeeeee"


def canvas(w, h, title):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w * 10)
    ax.set_ylim(0, h * 10)
    ax.axis("off")
    ax.set_title(title, fontsize=14, fontweight="bold")
    return fig, ax


def box(ax, x, y, w, h, text, color=BLUE, rounded=True, fs=9):
    style = "round,pad=0.3" if rounded else "square,pad=0.1"
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style, fc=color, ec="#333", lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, wrap=True)
    return (x, y, w, h)


def arrow(ax, p1, p2, label="", fs=8, style="-|>", ls="-"):
    ax.annotate("", xy=p2, xytext=p1, arrowprops=dict(arrowstyle=style, lw=1.2, color="#333", ls=ls))
    if label:
        ax.text((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 + 0.8, label, ha="center", fontsize=fs,
                bbox=dict(fc="white", ec="none", pad=0.5))


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=160)
    plt.close(fig)


def architecture():
    fig, ax = canvas(12, 7.2, "EvalRAG system architecture")
    box(ax, 2, 52, 16, 9, "Developer\n(edits prompt / model /\nconfig / documents)", ORANGE)
    box(ax, 26, 52, 18, 9, "GitHub repository\n+ GitHub Actions\n(CI/CD workflow)", ORANGE)
    box(ax, 2, 30, 16, 12, "Dataset & Config\nmodule\n(dataset.json,\nconfigs/*.json)")
    box(ax, 26, 30, 18, 12, "Evaluation Runner\n(evalrag.runner)")
    box(ax, 52, 30, 18, 12, "RAG application\nunder test\nRetriever (TF-IDF)\n+ Generator", GREEN)
    box(ax, 78, 30, 18, 12, "Knowledge base\n(data/kb/*.md)", GREEN)
    box(ax, 26, 10, 18, 12, "Metrics module\n(precision, recall,\nfaithfulness,\nrelevance, correctness)")
    box(ax, 52, 10, 18, 12, "Result storage\nSQLite / PostgreSQL\n(runs, case_results,\nmetric_scores)", GREY)
    box(ax, 78, 10, 18, 12, "Comparison engine\n+ Quality gate\n(PASS / WARN / FAIL)")
    box(ax, 101, 10, 17, 12, "Dashboard\n(Streamlit)\n+ REST API\n(FastAPI)", ORANGE)
    arrow(ax, (18, 56), (26, 56), "git push / PR")
    arrow(ax, (35, 52), (35, 42), "runs CLI")
    arrow(ax, (18, 36), (26, 36), "test cases")
    arrow(ax, (44, 36), (52, 36), "question")
    arrow(ax, (70, 36), (78, 36), "retrieve")
    arrow(ax, (35, 30), (35, 22), "answer + contexts")
    arrow(ax, (44, 16), (52, 16), "scores")
    arrow(ax, (70, 16), (78, 16), "run summary")
    arrow(ax, (96, 13), (101, 13), "")
    ax.plot([96, 99, 99, 35, 35], [20, 20, 66, 66, 62], color="#333", lw=1.2, ls="--")
    arrow(ax, (35, 63), (35, 61.5))
    ax.text(70, 67, "exit code 0/1 + markdown report back to CI", ha="center", fontsize=8,
            bbox=dict(fc="white", ec="none", pad=0.5))
    save(fig, "architecture.png")


def use_case():
    fig, ax = canvas(11, 7, "Use-case diagram")
    ax.add_patch(FancyBboxPatch((28, 4), 52, 62, boxstyle="square,pad=0", fc="white", ec="#333"))
    ax.text(54, 63, "EvalRAG system", ha="center", fontsize=11, fontweight="bold")

    def actor(x, y, name):
        ax.add_patch(plt.Circle((x, y + 6), 1.6, fc="white", ec="#333"))
        ax.plot([x, x], [y + 4.4, y], color="#333")
        ax.plot([x - 2.5, x + 2.5], [y + 3, y + 3], color="#333")
        ax.plot([x, x - 2], [y, y - 3], color="#333")
        ax.plot([x, x + 2], [y, y - 3], color="#333")
        ax.text(x, y - 6, name, ha="center", fontsize=9)

    cases = ["Upload / edit test dataset", "Configure RAG app & thresholds", "Run evaluation",
             "View metrics & latency", "Compare run with baseline", "Mark run as baseline",
             "Trigger evaluation on push/PR", "Apply quality gate (pass/fail)"]
    pos = {}
    for i, c in enumerate(cases):
        y = 57 - i * 7
        ax.add_patch(Ellipse((54, y), 34, 5.5, fc=BLUE, ec="#333"))
        ax.text(54, y, c, ha="center", va="center", fontsize=9)
        pos[c] = y
    actor(12, 44, "AI/ML Developer")
    actor(12, 18, "Team lead /\nProduct team")
    actor(96, 18, "CI system\n(GitHub Actions)")
    for c in cases[:6]:
        ax.plot([15, 37], [47, pos[c]], color="#555", lw=0.8)
    for c in ["View metrics & latency", "Compare run with baseline"]:
        ax.plot([15, 37], [21, pos[c]], color="#555", lw=0.8)
    for c in ["Run evaluation", "Trigger evaluation on push/PR", "Apply quality gate (pass/fail)"]:
        ax.plot([93, 71], [21, pos[c]], color="#555", lw=0.8)
    save(fig, "use_case.png")


def dfd0():
    fig, ax = canvas(11, 5, "DFD Level 0 (context diagram)")
    box(ax, 40, 18, 28, 14, "0\nEvalRAG\nEvaluation System", BLUE)
    box(ax, 2, 32, 22, 9, "Developer", ORANGE, rounded=False)
    box(ax, 2, 6, 22, 9, "GitHub Actions", ORANGE, rounded=False)
    box(ax, 84, 32, 22, 9, "RAG application", GREEN, rounded=False)
    box(ax, 84, 6, 22, 9, "Team lead", ORANGE, rounded=False)
    arrow(ax, (24, 38), (40, 29), "dataset, config,\nthresholds")
    arrow(ax, (40, 25), (24, 34), "")
    ax.text(31, 24, "reports", fontsize=8)
    arrow(ax, (24, 13), (40, 21), "trigger")
    arrow(ax, (40, 18.5), (24, 8))
    ax.text(31, 9, "pass/fail", fontsize=8)
    arrow(ax, (68, 29), (84, 38), "questions")
    arrow(ax, (84, 34), (68, 26), "")
    ax.text(73, 27, "answers +\ncontexts", fontsize=8)
    arrow(ax, (68, 21), (84, 11), "dashboard,\ncomparisons")
    save(fig, "dfd_level0.png")


def dfd1():
    fig, ax = canvas(12, 7, "DFD Level 1")
    p = {}
    p[1] = box(ax, 4, 44, 18, 10, "1.0\nLoad dataset\n& config")
    p[2] = box(ax, 32, 44, 18, 10, "2.0\nExecute test cases\non RAG app")
    p[3] = box(ax, 60, 44, 18, 10, "3.0\nCalculate metrics\n& latency")
    p[4] = box(ax, 60, 18, 18, 10, "4.0\nStore run")
    p[5] = box(ax, 32, 18, 18, 10, "5.0\nCompare with\nbaseline + gate")
    p[6] = box(ax, 4, 18, 18, 10, "6.0\nShow dashboard\n/ report")
    box(ax, 60, 2, 18, 6, "D1  Results DB", GREY, rounded=False)
    box(ax, 30, 1, 22, 5, "GitHub Actions (CI)", ORANGE, rounded=False)
    box(ax, 4, 60, 18, 6, "D2  dataset.json", GREY, rounded=False)
    box(ax, 32, 60, 18, 6, "RAG application", GREEN, rounded=False)
    arrow(ax, (13, 60), (13, 54), "")
    arrow(ax, (22, 49), (32, 49), "test cases")
    arrow(ax, (38, 54), (38, 60), "")
    arrow(ax, (44, 60), (44, 54), "")
    ax.text(52, 56.5, "question / answer + contexts", fontsize=8)
    arrow(ax, (50, 47), (60, 47), "outputs")
    arrow(ax, (69, 44), (69, 28), "scores")
    arrow(ax, (69, 18), (69, 8), "run record")
    arrow(ax, (60, 6), (50, 19), "baseline +\ncandidate")
    arrow(ax, (32, 23), (22, 23), "status, diff")
    arrow(ax, (41, 18), (41, 6), "pass / fail")
    save(fig, "dfd_level1.png")


def er():
    fig, ax = canvas(12, 6, "Database design (ER diagram)")

    def table(x, y, name, cols):
        h = 6 + 3.2 * len(cols)
        ax.add_patch(FancyBboxPatch((x, y - h), 30, h, boxstyle="square,pad=0", fc="white", ec="#333"))
        ax.add_patch(FancyBboxPatch((x, y - 4), 30, 4, boxstyle="square,pad=0", fc=BLUE, ec="#333"))
        ax.text(x + 15, y - 2, name, ha="center", va="center", fontweight="bold", fontsize=10)
        for i, c in enumerate(cols):
            ax.text(x + 1.5, y - 6.5 - i * 3.2, c, fontsize=8.5, va="center")

    table(3, 52, "runs", ["PK run_id  INTEGER", "version  TEXT", "dataset  TEXT", "config_json  TEXT",
                          "git_commit  TEXT", "started_at  TEXT", "status  TEXT", "is_baseline  INTEGER"])
    table(45, 52, "case_results", ["PK id  INTEGER", "FK run_id → runs", "case_id  TEXT", "question  TEXT",
                                   "answer  TEXT", "contexts_json  TEXT", "latency_ms  REAL", "error  TEXT"])
    table(87, 42, "metric_scores", ["PK id  INTEGER", "FK result_id → case_results", "metric  TEXT", "score  REAL"])
    arrow(ax, (33, 40), (45, 40), "1 : N", style="-")
    arrow(ax, (75, 34), (87, 34), "1 : N", style="-")
    save(fig, "er_diagram.png")


def sequence():
    fig, ax = canvas(12, 7, "Sequence diagram: push → CI evaluation → quality gate")
    actors = ["Developer", "GitHub Actions", "EvalRAG CLI", "RAG app", "Metrics", "Database"]
    xs = [8 + i * 21 for i in range(len(actors))]
    for x, a in zip(xs, actors):
        box(ax, x - 8, 62, 16, 5, a, ORANGE if i == 0 else BLUE, fs=8.5) if (i := actors.index(a)) is not None else None
        ax.plot([x, x], [4, 62], color="#999", ls="--", lw=0.8)
    msgs = [(0, 1, "git push / open PR"), (1, 2, "evalrag run --set-baseline"), (1, 2, "evalrag run (candidate)"),
            (2, 3, "answer(question) ×25"), (3, 2, "answer + contexts", True), (2, 4, "score_case()"),
            (4, 2, "scores", True), (2, 5, "save_run()"), (1, 2, "evalrag gate"), (2, 5, "load baseline + candidate"),
            (2, 1, "exit 0 = PASS / exit 1 = FAIL", True), (1, 0, "✓ / ✗ check on commit / PR", True)]
    y = 58
    for m in msgs:
        a, b, label = m[:3]
        arrow(ax, (xs[a], y), (xs[b], y), label, ls="--" if len(m) > 3 else "-")
        y -= 4.6
    save(fig, "sequence.png")


def flowchart():
    fig, ax = canvas(8, 10, "Quality-gate flowchart")
    steps = [("Start: code / prompt / config change pushed", ORANGE), ("Load dataset & config", BLUE),
             ("Run every test question through RAG app", BLUE), ("Compute metrics + latency per case", BLUE),
             ("Save run in database", BLUE), ("Load baseline run", BLUE)]
    y = 90
    for i, (s, c) in enumerate(steps):
        box(ax, 15, y, 50, 6, s, c)
        if i:
            arrow(ax, (40, y + 10), (40, y + 6))
        y -= 10
    ax.add_patch(plt.Polygon([[40, 35], [64, 26], [40, 17], [16, 26]], fc=GREEN, ec="#333"))
    ax.text(40, 26, "Errors? Score < minimum?\nDrop > 10% vs baseline?", ha="center", va="center", fontsize=8.5)
    arrow(ax, (40, 40), (40, 35))
    box(ax, 2, 4, 26, 6, "FAIL → exit 1\nblock merge / deploy", "#f6c9c9")
    box(ax, 52, 4, 26, 6, "PASS → exit 0\nallow merge / deploy", "#c9f0cf")
    arrow(ax, (25, 22), (15, 10), "yes")
    arrow(ax, (55, 22), (65, 10), "no")
    save(fig, "flowchart.png")


def class_diagram():
    fig, ax = canvas(12, 6.2, "Class / module diagram")

    def cls(x, y, name, attrs, ops):
        lines = attrs + ["—" * 12] + ops
        h = 6.5 + 2.8 * len(lines)
        ax.add_patch(FancyBboxPatch((x, y - h), 26, h, boxstyle="square,pad=0", fc="white", ec="#333"))
        ax.add_patch(FancyBboxPatch((x, y - 4.5), 26, 4.5, boxstyle="square,pad=0", fc=BLUE, ec="#333"))
        ax.text(x + 13, y - 2.2, name, ha="center", va="center", fontweight="bold", fontsize=9.5)
        for i, l in enumerate(lines):
            ax.text(x + 1.2, y - 6.8 - i * 2.8, l, fontsize=7.8, va="center")

    cls(2, 56, "RAGApp", ["config: dict", "chunks: list", "vectorizer"],
        ["retrieve(question)", "generate(question, ctx)", "answer(question)"])
    cls(32, 56, "runner", ["—"], ["load_dataset(path)", "run_evaluation(config,", "   dataset, conn)"])
    cls(62, 56, "metrics", ["METRIC_NAMES"], ["context_precision()", "context_recall()", "faithfulness()",
                                              "answer_relevance()", "answer_correctness()", "score_case()"])
    cls(92, 56, "storage", ["DB_PATH", "SCHEMA"], ["save_run()", "run_summary()", "set_baseline()", "list_runs()"])
    cls(32, 24, "compare", ["—"], ["compare(base, cand)", "quality_gate(cand,", "   thresholds, base)"])
    cls(62, 24, "cli / api / dashboard", ["—"], ["run, compare, gate", "GET/POST /runs", "Streamlit pages"])
    arrow(ax, (32, 50), (28, 50), "uses")
    arrow(ax, (58, 50), (62, 50), "uses")
    ax.plot([45, 45, 105, 105], [56.6, 58.5, 58.5, 56.6], color="#333", lw=1.2, ls="--")
    ax.text(75, 59, "saves via", ha="center", fontsize=8, bbox=dict(fc="white", ec="none", pad=0.3))
    arrow(ax, (62, 18), (58, 18), "uses")
    arrow(ax, (88, 18), (100, 30), "reads", ls="--")
    save(fig, "class_diagram.png")


if __name__ == "__main__":
    for f in (architecture, use_case, dfd0, dfd1, er, sequence, flowchart, class_diagram):
        f()
    print("diagrams written to", OUT)
