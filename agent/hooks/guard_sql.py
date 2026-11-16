#!/usr/bin/env python3
"""PreToolUse hook: audit log + best-effort pre-filter for the agent's SQL.

Logs every tool call and denies anything that does not look like a single
read-only query against the mart dataset. This is a regex filter, not a SQL
parser: the enforcing layers are MCP Toolbox (readOnly + allowedDatasets) and
the mart-reader IAM role. The hook fails closed: any error denies the call.

Claude Code contract: exit 2 = deny (stderr is shown to the model), exit 0 = allow.
"""
import datetime
import json
import os
import pathlib
import re
import sys

ALLOWED_TOOL = "mcp__bigquery__execute_sql"
# Claude Code's internal tool for --json-schema output: returns the answer, touches no data.
PASSTHROUGH = {"StructuredOutput"}
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|merge|create|drop|alter|truncate|grant|revoke|"
    r"export|load|call|execute|declare|set|begin|commit)\b", re.I)
OTHER_DATASETS = re.compile(r"(bigquery-public-data|\braw\.|\bcore\.|information_schema)", re.I)
COMMENTS = re.compile(r"--[^\n]*|#[^\n]*|/\*.*?\*/", re.S)
STRINGS = re.compile(r"'''.*?'''|\"\"\".*?\"\"\"|'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"", re.S)


def check(event):
    """Return a deny reason, or None to allow."""
    tool = event.get("tool_name", "")
    if tool in PASSTHROUGH:
        return None
    if tool != ALLOWED_TOOL:
        return f"tool {tool!r} is not allowed"
    sql = (event.get("tool_input") or {}).get("sql") or ""
    # Strip strings before comments so '#' or '--' inside a literal is not treated as a comment.
    stmt = COMMENTS.sub(" ", STRINGS.sub("''", sql)).strip().rstrip(";").strip()
    unquoted = stmt.replace("`", "")  # `p`.`core`.`t` -> p.core.t
    if not re.match(r"^(select|with)\b", stmt, re.I):
        return "only SELECT/WITH queries are allowed"
    if ";" in stmt:
        return "only a single statement is allowed"
    m = FORBIDDEN.search(stmt)
    if m:
        return f"forbidden keyword: {m.group(0)}"
    if OTHER_DATASETS.search(unquoted):
        return "only the mart dataset may be queried"
    return None


def log(event, reason):
    log_dir = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / "agent" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / "queries.jsonl", "a") as f:
        f.write(json.dumps({
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "session": event.get("session_id"),
            "tool": event.get("tool_name"),
            "sql": (event.get("tool_input") or {}).get("sql"),
            "blocked": reason,
        }) + "\n")


def main():
    event = {}
    try:
        event = json.load(sys.stdin)
        reason = check(event)
    except Exception as e:  # fail closed
        reason = f"guard error: {e}"
    if event.get("tool_name") not in PASSTHROUGH:
        try:
            log(event, reason)
        except Exception as e:  # an unloggable call is not allowed through
            reason = reason or f"could not write query log: {e}"
    if reason:
        print(f"Blocked by guardrail: {reason}", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
