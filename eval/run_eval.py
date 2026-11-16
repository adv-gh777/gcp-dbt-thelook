#!/usr/bin/env python3
"""Evaluate the analytics agent against hand-written ground-truth SQL.

  python eval/run_eval.py --refresh-expected        # recompute expected answers from the marts
  python eval/run_eval.py --label baseline          # run all questions through ./ask --json
  python eval/run_eval.py --label v2 --only q15,q22 # subset

Questions run sequentially (gentle on Claude plan limits). Results go to eval/results/<label>.{json,md}.
"""
import argparse, json, os, pathlib, statistics, subprocess, sys, time
from collections import Counter

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "eval" / "questions.yaml"
EXPECTED = ROOT / "eval" / "expected.json"
RESULTS = ROOT / "eval" / "results"
QUERY_LOG = ROOT / "agent" / "logs" / "queries.jsonl"
REL_TOL, ABS_TOL = 1e-4, 0.01  # 0.01% relative, or 1 cent (expected values are exact; agent rounds to 2 dp)
TIMEOUT_S = 600


def refresh_expected(questions, project):
    from google.cloud import bigquery
    client = bigquery.Client(project=project)
    cfg = bigquery.QueryJobConfig(maximum_bytes_billed=1_000_000_000)
    out = {}
    for q in questions:
        rows = list(client.query(q["sql"].format(p=project), job_config=cfg).result())
        if q["type"] == "scalar":
            out[q["id"]] = {"value": float(rows[0]["value"])}
        else:
            out[q["id"]] = {"rows": [{"label": str(r["label"]), "value": float(r["value"])} for r in rows]}
        print(f"{q['id']}: {out[q['id']]}")
    EXPECTED.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {EXPECTED.relative_to(ROOT)}")


def close(a, e):
    return a is not None and abs(a - e) <= max(REL_TOL * abs(e), ABS_TOL)


def norm(label):
    return str(label).strip().casefold()


def grade(q, exp, ans):
    """Return (passed, failure_category)."""
    if ans is None:
        return False, "no_structured_answer"
    rows = ans.get("rows") or []
    if q["type"] == "scalar":
        value = ans.get("value")
        if value is None and len(rows) == 1:
            value = rows[0]["value"]
        if value is None:
            return False, "no_answer"
        return (True, None) if close(value, exp["value"]) else (False, "wrong_value")
    if q["type"] == "top1":
        if not rows:
            return False, "no_answer"
        best = max(rows, key=lambda r: r["value"])
        e = exp["rows"][0]
        if norm(best["label"]) != norm(e["label"]):
            return False, "wrong_labels"
        return (True, None) if close(best["value"], e["value"]) else (False, "wrong_value")
    # rows: same label set, every value within tolerance
    got = {norm(r["label"]): r["value"] for r in rows}
    want = {norm(r["label"]): r["value"] for r in exp["rows"]}
    if set(got) != set(want):
        return False, "wrong_labels"
    return (True, None) if all(close(got[k], want[k]) for k in want) else (False, "wrong_value")


def queries_for(session_id):
    if not session_id or not QUERY_LOG.exists():
        return []
    return [e for e in map(json.loads, QUERY_LOG.read_text().splitlines()) if e.get("session") == session_id]


def ask(question):
    prompt = (f"{question}\n\nReturn the structured answer: a single number in `value` (with `rows` empty), "
              "or a list/breakdown in `rows` (with `value` null). Percentages as plain numbers "
              "(12.5 means 12.5%). Do not round beyond 2 decimals.")
    start = time.monotonic()
    try:
        proc = subprocess.run([str(ROOT / "ask"), "--json", prompt], capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return None, time.monotonic() - start, {"error": f"timeout after {TIMEOUT_S}s", "timeout": True}
    latency = time.monotonic() - start
    try:
        env = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None, latency, {"error": (proc.stderr or proc.stdout)[-500:]}
    return env.get("structured_output"), latency, env


def run(questions, expected, label):
    results = []
    for i, q in enumerate(questions, 1):
        ans, latency, env = ask(q["question"])
        passed, failure = grade(q, expected[q["id"]], ans)
        qs = [e for e in queries_for(env.get("session_id")) if e["tool"].startswith("mcp__")]
        if env.get("timeout"):
            failure = "timeout"
        elif "error" in env or env.get("is_error"):
            failure = failure and "agent_error"
        elif not passed and not qs:
            failure = "no_query_executed"  # answered (or gave up) without running any SQL
        results.append({
            "id": q["id"], "category": q["category"], "question": q["question"],
            "passed": passed, "failure": failure, "latency_s": round(latency, 1),
            "num_turns": env.get("num_turns"), "queries": len(qs),
            "blocked_queries": sum(1 for e in qs if e.get("blocked")),
            "expected": expected[q["id"]], "answer": ans,
            "error": env.get("error") or (env.get("result") if env.get("is_error") else None),
        })
        print(f"[{i:02}/{len(questions)}] {q['id']} {'PASS' if passed else 'FAIL ' + str(failure):<22} "
              f"{latency:5.1f}s  {q['question']}", flush=True)
    return results


def report(results, label):
    n = len(results)
    passed = sum(r["passed"] for r in results)
    lat = [r["latency_s"] for r in results]
    by_cat = {}
    for r in results:
        c = by_cat.setdefault(r["category"], [0, 0])
        c[0] += r["passed"]; c[1] += 1
    failures = Counter(r["failure"] for r in results if not r["passed"])
    summary = {
        "label": label, "questions": n, "passed": passed, "accuracy": round(passed / n, 3),
        "latency_median_s": round(statistics.median(lat), 1), "latency_p90_s": round(statistics.quantiles(lat, n=10)[-1], 1) if n > 1 else lat[0],
        "by_category": {k: f"{v[0]}/{v[1]}" for k, v in by_cat.items()},
        "failures": dict(failures),
    }
    RESULTS.mkdir(exist_ok=True)
    body = json.dumps({"summary": summary, "results": results}, indent=2) + "\n"
    project = os.environ.get("GCP_PROJECT")
    if project:  # keep the project id out of committed results
        body = body.replace(project, "<project>")
    (RESULTS / f"{label}.json").write_text(body)
    md = [f"# Eval: {label}", "",
          f"**Accuracy: {passed}/{n} ({100 * passed / n:.0f}%)**, median latency {summary['latency_median_s']}s, "
          f"p90 {summary['latency_p90_s']}s", "",
          "| Category | Passed |", "|---|---|", *[f"| {k} | {v} |" for k, v in summary["by_category"].items()], "",
          "| Failure | Count |", "|---|---|", *[f"| {k} | {v} |" for k, v in failures.items()], "",
          "| id | result | latency (s) | queries | question |", "|---|---|---|---|---|",
          *[f"| {r['id']} | {'PASS' if r['passed'] else 'FAIL: ' + str(r['failure'])} | {r['latency_s']} | "
            f"{r['queries']} | {r['question']} |" for r in results]]
    (RESULTS / f"{label}.md").write_text("\n".join(md) + "\n")
    print(json.dumps(summary, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh-expected", action="store_true")
    ap.add_argument("--label", default="run")
    ap.add_argument("--only", help="comma-separated question ids")
    ap.add_argument("--regrade", metavar="LABEL", help="re-score saved answers in results/LABEL.json with the current grader")
    args = ap.parse_args()

    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        sys.exit("ERROR: ANTHROPIC_API_KEY/ANTHROPIC_AUTH_TOKEN is set. Unset it so the agent "
                 "runs on your Claude subscription login.")
    project = os.environ.get("GCP_PROJECT") or sys.exit("ERROR: set GCP_PROJECT")

    questions = yaml.safe_load(QUESTIONS.read_text())
    qmap = {q["id"]: q for q in questions}
    if args.refresh_expected:
        return refresh_expected(questions, project)
    if args.only:
        ids = set(args.only.split(","))
        questions = [q for q in questions if q["id"] in ids]
    expected = json.loads(EXPECTED.read_text())
    if args.regrade:
        saved = json.loads((RESULTS / f"{args.regrade}.json").read_text())["results"]
        for r in saved:
            r["passed"], r["failure"] = grade(qmap[r["id"]], expected[r["id"]], r["answer"])
            if not r["passed"] and not r["queries"]:
                r["failure"] = "no_query_executed"
        return report(saved, args.regrade)
    report(run(questions, expected, args.label), args.label)


if __name__ == "__main__":
    main()
