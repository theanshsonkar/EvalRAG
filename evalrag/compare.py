"""Compares a candidate run with the baseline and applies the quality gate."""


def compare(baseline, candidate):
    rows = []
    for metric in sorted(set(baseline["metrics"]) | set(candidate["metrics"])):
        b, c = baseline["metrics"].get(metric), candidate["metrics"].get(metric)
        rows.append({"metric": metric, "baseline": b, "candidate": c,
                     "change": None if b is None or c is None else c - b})
    rows.append({"metric": "avg_latency_ms", "baseline": baseline["avg_latency_ms"],
                 "candidate": candidate["avg_latency_ms"],
                 "change": candidate["avg_latency_ms"] - baseline["avg_latency_ms"]})
    return rows


def quality_gate(candidate, thresholds, baseline=None):
    """Returns (status, reasons). status is PASS, WARN or FAIL."""
    failures, warnings = [], []
    if candidate["errors"]:
        failures.append(f"{candidate['errors']} test case(s) raised errors")
    for metric, minimum in thresholds.get("min_scores", {}).items():
        score = candidate["metrics"].get(metric)
        if score is None:
            failures.append(f"{metric}: not computed")
        elif score < minimum:
            failures.append(f"{metric} = {score:.3f} is below the minimum {minimum:.2f}")
    max_lat = thresholds.get("max_avg_latency_ms")
    if max_lat and candidate["avg_latency_ms"] > max_lat:
        failures.append(f"avg latency {candidate['avg_latency_ms']:.1f} ms is above {max_lat} ms")
    max_drop = thresholds.get("max_drop_vs_baseline")
    if baseline and max_drop is not None and baseline["run_id"] != candidate["run_id"]:
        for metric, b in baseline["metrics"].items():
            c = candidate["metrics"].get(metric)
            if c is not None and b - c > max_drop:
                failures.append(f"{metric} dropped by {b - c:.3f} vs baseline run {baseline['run_id']} (allowed {max_drop:.2f})")
            elif c is not None and b - c > max_drop / 2:
                warnings.append(f"{metric} dropped by {b - c:.3f} vs baseline")
    if failures:
        return "FAIL", failures
    return ("WARN", warnings) if warnings else ("PASS", ["all checks passed"])
