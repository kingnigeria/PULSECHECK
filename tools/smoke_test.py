from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def main() -> int:
    server = subprocess.Popen(
        [PYTHON, "server.py", "--config", "config\\manager.json"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    time.sleep(2)
    worker = subprocess.Popen(
        [PYTHON, "client.py", "--config", "config\\worker.json"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        time.sleep(14)
    finally:
        worker.kill()
        server.kill()

    server_out, server_err = server.communicate()
    worker_out, worker_err = worker.communicate()
    combined = "\n".join([server_out, server_err, worker_out, worker_err])

    expected = [
        "Authenticated worker",
        "opened data channel",
        "Metrics from worker-1",
        "Heartbeat from worker-1",
    ]
    missing = [item for item in expected if item not in combined]
    if missing:
        print("Smoke test failed. Missing log lines:")
        for item in missing:
            print(f"- {item}")
        print("\nCaptured output:\n")
        print(combined)
        return 1

    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
