# EvalRAG report: run 3 (v2-bad-change)

**Quality gate: FAIL**

- answer_relevance = 0.100 is below the minimum 0.30
- answer_correctness = 0.234 is below the minimum 0.60
- answer_correctness dropped by 0.646 vs baseline run 1 (allowed 0.10)
- answer_relevance dropped by 0.266 vs baseline run 1 (allowed 0.10)

Cases: 25, errors: 0, avg latency: 0.4 ms

Compared with baseline run 1 (v1-baseline):

| Metric | Baseline | Candidate | Change |
|---|---|---|---|
| answer_correctness | 0.880 | 0.234 | -0.646 |
| answer_relevance | 0.366 | 0.100 | -0.266 |
| context_precision | 0.547 | 1.000 | 0.453 |
| context_recall | 1.000 | 1.000 | 0.000 |
| faithfulness | 1.000 | 1.000 | 0.000 |
| avg_latency_ms | 1.377 | 0.387 | -0.990 |
