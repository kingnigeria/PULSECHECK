#!/usr/bin/env python3
"""
PulseCheck Demo Setup Script

This launcher is intentionally defensive:
- it uses paths relative to this file instead of the current terminal folder
- it finds a Python runtime that already has the required packages
- it starts manager and workers as subprocesses
- it waits for the dashboard to come up before claiming success
"""

from __future__ import annotations

import json
import os
import argparse
import platform
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "config"
DIST_CONFIG_DIR = ROOT / "dist" / "config"
LOGS_DIR = ROOT / "logs"
REQUIRED_IMPORTS = "import psutil, cryptography"


def get_local_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip_address = sock.getsockname()[0]
        sock.close()
        return ip_address
    except OSError:
        return "127.0.0.1"


def print_header() -> None:
    print("\n" + "=" * 60)
    print("   PulseCheck Demo Setup - Automated Configuration")
    print("=" * 60 + "\n")


def candidate_pythons() -> list[Path]:
    seen: set[str] = set()
    candidates: list[Path] = []
    direct_candidates = [
        ROOT / ".venv" / "Scripts" / "python.exe",
        Path(sys.executable),
        Path(os.environ.get("LocalAppData", "")) / "Programs" / "Python" / "Python312" / "python.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Python312" / "python.exe",
        Path(os.environ.get("LocalAppData", "")) / "Python" / "pythoncore-3.14-64" / "python.exe",
        Path(r"C:\Users\harus\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"),
    ]
    for candidate in direct_candidates:
        candidate_str = str(candidate)
        if candidate_str and safe_exists(candidate) and candidate_str not in seen:
            seen.add(candidate_str)
            candidates.append(candidate)

    for command in (["where", "python"], ["where", "py"]):
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
        except OSError:
            continue
        for line in result.stdout.splitlines():
            path = Path(line.strip())
            path_str = str(path)
            if path_str and safe_exists(path) and path_str not in seen:
                seen.add(path_str)
                candidates.append(path)
    return candidates


def safe_exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def has_required_packages(python_path: Path) -> bool:
    try:
        result = subprocess.run(
            [str(python_path), "-c", REQUIRED_IMPORTS],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def resolve_runtime() -> Path:
    for candidate in candidate_pythons():
        if has_required_packages(candidate):
            return candidate
    raise RuntimeError(
        "No usable Python runtime was found with psutil and cryptography installed. "
        "Run install_pulsecheck.bat first."
    )


def update_config_files(manager_ip: str) -> None:
    print("Updating config files with IP: " + manager_ip)
    config_files = [
        CONFIG_DIR / "manager.json",
        CONFIG_DIR / "worker.json",
        CONFIG_DIR / "worker-2.json",
        DIST_CONFIG_DIR / "manager.json",
        DIST_CONFIG_DIR / "worker.json",
        DIST_CONFIG_DIR / "worker-2.json",
    ]

    updated = 0
    for config_path in config_files:
        if not config_path.exists():
            continue
        with config_path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)
        if "worker" in config_path.name:
            config["manager_host"] = manager_ip
        elif "manager" in config_path.name:
            config["host"] = "0.0.0.0"
        with config_path.open("w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2)
        print("   OK: " + str(config_path.relative_to(ROOT)))
        updated += 1

    print("\nUpdated " + str(updated) + " config files\n")


def setup_firewall() -> None:
    if platform.system() != "Windows":
        print("Skipping firewall setup (not Windows)\n")
        return

    print("Setting up Windows Firewall rules...")
    print("   You may be prompted for Administrator permission\n")

    rules = [
        (
            'netsh advfirewall firewall add rule name="PulseCheck TCP" dir=in action=allow protocol=tcp localport=8001,8002,5000 enable=yes',
            "TCP ports",
        ),
        (
            'netsh advfirewall firewall add rule name="PulseCheck UDP" dir=in action=allow protocol=udp localport=8003 enable=yes',
            "UDP port",
        ),
    ]

    for rule, description in rules:
        try:
            subprocess.run(rule, shell=True, check=False, capture_output=True)
            print("   OK: " + description)
        except OSError as exc:
            print("   Warning " + description + ": " + str(exc))

    print()


def launch_process(python_path: Path, script_name: str, log_name: str, *args: str) -> subprocess.Popen[str]:
    LOGS_DIR.mkdir(exist_ok=True)
    log_path = LOGS_DIR / log_name
    log_handle = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [str(python_path), str(ROOT / script_name), *args],
        cwd=str(ROOT),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    process._pulsecheck_log_handle = log_handle  # type: ignore[attr-defined]
    process._pulsecheck_log_path = log_path  # type: ignore[attr-defined]
    return process


def process_failed(process: subprocess.Popen[str], label: str) -> bool:
    if process.poll() is None:
        return False
    log_path = getattr(process, "_pulsecheck_log_path", None)
    print(f"{label} exited early.")
    if log_path and Path(log_path).exists():
        print("   See log: " + str(log_path))
    return True


def wait_for_dashboard(manager_ip: str, timeout_seconds: int = 15) -> bool:
    deadline = time.time() + timeout_seconds
    url = f"http://{manager_ip}:5000/healthz"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                return response.status == 200
        except urllib.error.URLError:
            time.sleep(1)
    return False


def open_dashboard(manager_ip: str) -> None:
    url = f"http://{manager_ip}:5000"
    print("Opening dashboard at " + url)
    try:
        if platform.system() == "Windows":
            os.startfile(url)
        elif platform.system() == "Darwin":
            subprocess.run(["open", url], check=False)
        else:
            subprocess.run(["xdg-open", url], check=False)
        print("   OK: Dashboard opened in browser\n")
    except OSError as exc:
        print("   Warning: Could not open browser: " + str(exc))
        print("   Visit manually: " + url + "\n")


def show_instructions(manager_ip: str, python_path: Path, local_workers: int) -> None:
    print("=" * 60)
    print("   SETUP COMPLETE - DEMO IS RUNNING")
    print("=" * 60)
    print(
        f"""
Manager IP: {manager_ip}
Dashboard: http://{manager_ip}:5000
Python runtime: {python_path}

Running:
   - Manager Server (ports 8001, 8002, 8003, 5000)
   - {local_workers} local worker(s)
   - Web Dashboard

For video recording:
   1. Show the dashboard URL
   2. Refresh to see visitors and workers appear
   3. Show the recent event stream updating

To stop: Press Ctrl+C in this terminal
"""
    )
    print("=" * 60)


def terminate_processes(processes: list[subprocess.Popen[str]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    time.sleep(1)
    for process in processes:
        if process.poll() is None:
            process.kill()
        log_handle = getattr(process, "_pulsecheck_log_handle", None)
        if log_handle is not None:
            log_handle.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up the PulseCheck expo demo.")
    parser.add_argument(
        "--local-workers",
        type=int,
        choices=(0, 1, 2),
        default=1,
        help="How many local workers to launch on this machine. Default: 1",
    )
    args = parser.parse_args()

    print_header()
    manager_ip = get_local_ip()
    print("Detected Local IP: " + manager_ip + "\n")

    python_path = resolve_runtime()
    print("Using Python runtime: " + str(python_path) + "\n")

    update_config_files(manager_ip)
    setup_firewall()

    processes: list[subprocess.Popen[str]] = []
    try:
        print("Starting Manager Server...")
        manager = launch_process(python_path, "server.py", "manager.log", "--config", str(CONFIG_DIR / "manager.json"))
        processes.append(manager)
        time.sleep(2)
        if process_failed(manager, "Manager"):
            raise RuntimeError("Manager failed to start")

        if args.local_workers >= 1:
            print("Starting Worker 1...")
            worker_1 = launch_process(
                python_path,
                "client.py",
                "worker-1.log",
                "--config",
                str(CONFIG_DIR / "worker.json"),
            )
            processes.append(worker_1)
            time.sleep(1)
            if process_failed(worker_1, "Worker 1"):
                raise RuntimeError("Worker 1 failed to start")

        if args.local_workers >= 2:
            print("Starting Worker 2...")
            worker_2 = launch_process(
                python_path,
                "client.py",
                "worker-2.log",
                "--config",
                str(CONFIG_DIR / "worker-2.json"),
            )
            processes.append(worker_2)
            time.sleep(1)
            if process_failed(worker_2, "Worker 2"):
                raise RuntimeError("Worker 2 failed to start")

        print("\nWaiting for dashboard to become ready...\n")
        if not wait_for_dashboard(manager_ip):
            raise RuntimeError(
                "Dashboard did not come up on port 5000. Check logs\\manager.log for details."
            )

        open_dashboard(manager_ip)
        show_instructions(manager_ip, python_path, args.local_workers)

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down demo...")
    finally:
        terminate_processes(processes)


if __name__ == "__main__":
    main()
