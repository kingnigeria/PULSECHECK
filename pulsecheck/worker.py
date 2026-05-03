from __future__ import annotations

import argparse
import platform
import shlex
import socket
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import psutil

from .config import load_json, runtime_root
from .logging_utils import configure_logging
from .protocol import JsonSocket
from .security import build_fernet


class WorkerClient:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.log = configure_logging("pulsecheck.worker")
        self.fernet = build_fernet(config["fernet_key"])
        self.worker_id = config["worker_id"]
        self.manager_host = config["manager_host"]
        self.handshake_port = int(config["handshake_port"])
        self.data_port = int(config["data_port"])
        self.alert_port = int(config["alert_port"])
        self.heartbeat_interval = int(config["heartbeat_interval_seconds"])
        self.allow_commands = set(config.get("allow_commands", []))
        self.alert_thresholds = config.get("alert_thresholds", {})
        self.channel: JsonSocket | None = None
        self.send_lock = threading.Lock()

    def run(self) -> None:
        auth = self._authenticate()
        self.data_port = int(auth["data_port"])
        self.alert_port = int(auth["alert_port"])
        self._open_data_channel(auth["session_token"])
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        self._receive_loop()

    def _authenticate(self) -> dict[str, Any]:
        try:
            with socket.create_connection((self.manager_host, self.handshake_port), timeout=10) as sock:
                channel = JsonSocket(sock, self.fernet)
                channel.send(
                    {
                        "type": "auth",
                        "worker_id": self.worker_id,
                        "platform": platform.platform(),
                    }
                )
                response = channel.recv()
                if response.get("status") != "ok":
                    raise RuntimeError(f"Authentication failed: {response}")
                self.log.info("Authenticated with manager as %s", self.worker_id)
                return response
        except ConnectionRefusedError as exc:
            raise RuntimeError(
                f"Could not reach the manager at {self.manager_host}:{self.handshake_port}. "
                "Make sure the manager is running, the IP address is correct, and the firewall "
                "allows port 8001."
            ) from exc
        except TimeoutError as exc:
            raise RuntimeError(
                f"Timed out reaching the manager at {self.manager_host}:{self.handshake_port}. "
                "Check that both devices are on the same network and that the manager IP is correct."
            ) from exc

    def _open_data_channel(self, token: str) -> None:
        sock = socket.create_connection((self.manager_host, self.data_port), timeout=10)
        self.channel = JsonSocket(sock, self.fernet)
        self._send(
            {
                "type": "register_data",
                "worker_id": self.worker_id,
                "session_token": token,
            }
        )
        response = self.channel.recv()
        if response.get("status") != "ok":
            raise RuntimeError(f"Failed to open data channel: {response}")
        self.log.info("Data channel established to manager")

    def _receive_loop(self) -> None:
        if self.channel is None:
            raise RuntimeError("Data channel is not ready")
        while True:
            message = self.channel.recv()
            if message.get("type") != "task":
                self.log.info("Received control message: %s", message)
                continue
            result = self._execute_task(message)
            self._send(result)

    def _heartbeat_loop(self) -> None:
        while True:
            time.sleep(self.heartbeat_interval)
            try:
                self._send(
                    {
                        "type": "heartbeat",
                        "worker_id": self.worker_id,
                        "timestamp": time.time(),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                self.log.warning("Heartbeat failed: %s", exc)
                return

    def _execute_task(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action")
        argument = task.get("argument")
        if action == "collect_metrics":
            metrics = self._collect_metrics()
            self._send_alerts_if_needed(metrics)
            return {"type": "metrics", "worker_id": self.worker_id, **metrics}
        if action == "run_command":
            return self._run_command(argument or "")
        return {
            "type": "task_result",
            "worker_id": self.worker_id,
            "action": action,
            "output": f"Unsupported task: {action}",
            "success": False,
        }

    def _collect_metrics(self) -> dict[str, Any]:
        disk_root = Path.cwd().anchor or str(Path.home().anchor) or "/"
        disk = psutil.disk_usage(disk_root)
        boot_time = psutil.boot_time()
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": disk.percent,
            "boot_time": boot_time,
        }

    def _send_alerts_if_needed(self, metrics: dict[str, Any]) -> None:
        alerts: list[str] = []
        for field, threshold in self.alert_thresholds.items():
            value = float(metrics.get(field, 0.0))
            if value >= float(threshold):
                alerts.append(f"{field} threshold exceeded: {value:.1f}% >= {threshold}")
        for alert in alerts:
            self._send_udp_alert(alert)

    def _send_udp_alert(self, message: str) -> None:
        payload = self.fernet.encrypt(f"{self.worker_id}: {message}".encode("utf-8"))
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(payload, (self.manager_host, self.alert_port))

    def _run_command(self, raw_command: str) -> dict[str, Any]:
        if not raw_command:
            return self._task_result("run_command", "No command supplied", False)
        parts = shlex.split(raw_command, posix=False)
        command_name = parts[0].lower()
        if command_name not in self.allow_commands:
            return self._task_result(
                "run_command",
                f"Rejected unauthorized command: {raw_command}",
                False,
            )
        completed = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )
        output = completed.stdout.strip() or completed.stderr.strip() or "(no output)"
        return self._task_result("run_command", output, completed.returncode == 0)

    def _task_result(self, action: str, output: str, success: bool) -> dict[str, Any]:
        return {
            "type": "task_result",
            "worker_id": self.worker_id,
            "action": action,
            "output": output,
            "success": success,
        }

    def _send(self, payload: dict[str, Any]) -> None:
        if self.channel is None:
            raise RuntimeError("Data channel is not ready")
        with self.send_lock:
            self.channel.send(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PulseCheck worker.")
    default_config = runtime_root() / "config" / "worker.json"
    parser.add_argument("--config", default=str(default_config))
    args = parser.parse_args()
    config = load_json(args.config)
    WorkerClient(config).run()
