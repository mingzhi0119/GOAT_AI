#!/usr/bin/env python3
"""GOAT AI — chat log query tool.

Usage (run from any directory inside the project):
    python3 tools/query_logs.py recent          # last 20 conversations
    python3 tools/query_logs.py recent 50       # last N conversations
    python3 tools/query_logs.py stats           # daily usage counts
    python3 tools/query_logs.py search Porter   # keyword search in user messages
    python3 tools/query_logs.py export          # dump all rows as CSV to stdout
    python3 tools/query_logs.py export > logs.csv

DB path: reads GOAT_LOG_PATH env var, otherwise <project_root>/chat_logs.db
"""
from __future__ import annotations

import csv
import os
import sqlite3
import sys
import textwrap
from pathlib import Path

# ── Resolve DB path ───────────────────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_DEFAULT_DB = _PROJECT_ROOT / "chat_logs.db"
DB_PATH = Path(os.environ.get("GOAT_LOG_PATH", str(_DEFAULT_DB)))


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        sys.exit(f"[query_logs] DB not found: {DB_PATH}\nHas the server received any chat requests yet?")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _hr(width: int = 80) -> None:
    print("─" * width)


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_recent(n: int = 20) -> None:
    """Show the N most recent conversations (default 20)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, created_at, ip, model, turn_count, response_ms, user_message, assistant_response "
            "FROM conversations ORDER BY id DESC LIMIT ?",
            (n,),
        ).fetchall()

    if not rows:
        print("No conversations logged yet.")
        return

    _hr()
    for row in rows:
        question = textwrap.shorten(row["user_message"], width=120, placeholder="…")
        answer   = textwrap.shorten(row["assistant_response"], width=120, placeholder="…")
        ms = f"{row['response_ms']} ms" if row["response_ms"] is not None else "—"
        print(f"[#{row['id']}] {row['created_at']}  |  {row['ip']}  |  {row['model']}  |  turns={row['turn_count']}  |  {ms}")
        print(f"  Q: {question}")
        print(f"  A: {answer}")
        _hr()


def cmd_stats() -> None:
    """Print daily conversation counts and average response time."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                date(created_at)          AS day,
                COUNT(*)                  AS conversations,
                ROUND(AVG(response_ms))   AS avg_ms
            FROM conversations
            GROUP BY day
            ORDER BY day DESC
            """
        ).fetchall()

    if not rows:
        print("No data yet.")
        return

    print(f"{'Date':<12} {'Conversations':>14} {'Avg response':>14}")
    _hr(42)
    for row in rows:
        avg = f"{int(row['avg_ms'])} ms" if row["avg_ms"] is not None else "—"
        print(f"{row['day']:<12} {row['conversations']:>14} {avg:>14}")

    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    print()
    print(f"Total conversations: {total}")


def cmd_search(keyword: str) -> None:
    """Search user messages containing keyword (case-insensitive)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, created_at, ip, model, user_message, assistant_response "
            "FROM conversations WHERE user_message LIKE ? ORDER BY id DESC",
            (f"%{keyword}%",),
        ).fetchall()

    print(f"Found {len(rows)} result(s) for '{keyword}':")
    _hr()
    for row in rows:
        question = textwrap.shorten(row["user_message"], width=120, placeholder="…")
        answer   = textwrap.shorten(row["assistant_response"], width=120, placeholder="…")
        print(f"[#{row['id']}] {row['created_at']}  |  {row['ip']}  |  {row['model']}")
        print(f"  Q: {question}")
        print(f"  A: {answer}")
        _hr()


def cmd_export() -> None:
    """Dump all rows as CSV to stdout.  Redirect to a file with > logs.csv"""
    with _connect() as conn:
        cur = conn.execute("SELECT * FROM conversations ORDER BY id")
        writer = csv.writer(sys.stdout)
        writer.writerow([d[0] for d in cur.description])
        writer.writerows(cur)


# ── Entry point ───────────────────────────────────────────────────────────────

_USAGE = textwrap.dedent("""\
    Usage:
      python3 tools/query_logs.py recent [N]     — last N conversations (default 20)
      python3 tools/query_logs.py stats          — daily counts + avg response time
      python3 tools/query_logs.py search KEYWORD — search user messages
      python3 tools/query_logs.py export         — dump all rows as CSV to stdout
""")

def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(_USAGE)
        sys.exit(0)

    cmd, *rest = args

    if cmd == "recent":
        n = int(rest[0]) if rest else 20
        cmd_recent(n)
    elif cmd == "stats":
        cmd_stats()
    elif cmd == "search":
        if not rest:
            sys.exit("Usage: query_logs.py search KEYWORD")
        cmd_search(" ".join(rest))
    elif cmd == "export":
        cmd_export()
    else:
        print(f"Unknown command: {cmd}\n")
        print(_USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
