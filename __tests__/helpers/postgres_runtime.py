from __future__ import annotations

import shutil
import socket
import subprocess
import time
import unittest
from contextlib import contextmanager
from uuid import uuid4

import psycopg


def _pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@contextmanager
def postgres_runtime_container():
    if shutil.which("docker") is None:
        raise unittest.SkipTest("docker CLI is required for Postgres runtime tests")

    port = _pick_port()
    name = f"goat-phase16d-{uuid4().hex[:12]}"
    run_cmd = [
        "docker",
        "run",
        "--rm",
        "-d",
        "--name",
        name,
        "-e",
        "POSTGRES_DB=goat",
        "-e",
        "POSTGRES_USER=goat",
        "-e",
        "POSTGRES_PASSWORD=secret",
        "-p",
        f"{port}:5432",
        "postgres:16-alpine",
    ]
    started = subprocess.run(run_cmd, capture_output=True, text=True)
    if started.returncode != 0:
        raise unittest.SkipTest(
            "docker is unavailable for Postgres runtime tests: "
            + started.stderr.strip()
        )

    dsn = f"postgresql://goat:secret@127.0.0.1:{port}/goat"
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                with psycopg.connect(dsn) as conn:
                    conn.execute("SELECT 1").fetchone()
                break
            except Exception:
                time.sleep(1)
        else:
            raise unittest.SkipTest("Timed out waiting for Postgres test container")
        yield dsn
    finally:
        subprocess.run(
            ["docker", "rm", "-f", name],
            capture_output=True,
            text=True,
        )
