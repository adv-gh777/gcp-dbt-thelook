#!/usr/bin/env python3
"""PreToolUse hook: logs every tool call and blocks anything that is not a
read-only query against the mart dataset. Defence in depth on top of
Toolbox's readOnly/allowedDatasets and the mart-reader IAM role."""
import json, os, re, sys, datetime, pathlib

ALLOWED_TOOL = "mcp__bigquery__execute_sql"
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|merge|create|drop|alter|truncate|grant|revoke|"
    r"export|load|call|execute|declare|set|begin|commit)\b", re.I)
OTHER_DATASETS = re.compile(r"(bigquery-public-data|\braw\.|\bcore\.|information_schema)", re.I)

event = json.load(sys.stdin)
tool = event.get("tool_name", "")
sql = (event.get("tool_input") or {}).get("sql", "")
no_comments = re.sub(r"--[^\n]*|/\*.*?\*/", " ", sql, flags=re.S)
no_strings = re.sub(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"", "''", no_comments)
stmt = no_strings.strip().rstrip(";").strip()

reason = None
if tool != ALLOWED_TOOL:
    reason = f"tool {tool!r} is not allowed"
elif event.get("tool_input", {}).get("dry_run"):
    reason = None
elif not re.match(r"^(select|with)\b", stmt, re.I):
    reason = "only SELECT/WITH queries are allowed"
elif ";" in stmt:
    reason = "only a single statement is allowed"
elif FORBIDDEN.search(stmt):
    reason = f"forbidden keyword: {FORBIDDEN.search(stmt).group(0)}"
elif OTHER_DATASETS.search(stmt):
    reason = "only the mart dataset may be queried"

log_dir = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / "agent" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
with open(log_dir / "queries.jsonl", "a") as f:
    f.write(json.dumps({
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "session": event.get("session_id"),
        "tool": tool,
        "sql": sql,
        "blocked": reason,
    }) + "\n")

if reason:
    print(f"Blocked by guardrail: {reason}", file=sys.stderr)
    sys.exit(2)  # exit 2 = deny the tool call and show the reason to the model
sys.exit(0)
