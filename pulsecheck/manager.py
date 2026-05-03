from __future__ import annotations

import argparse
import platform
import socket
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import load_json, resolve_from_config, runtime_root
from .logging_utils import configure_logging
from .protocol import JsonSocket
from .security import build_fernet, new_session_token
from .tasks import Task, load_tasks
from .web import DashboardServer


@dataclass
class WorkerSession:
    worker_id: str
    address: tuple[str, int]
    session_token: str
    platform_name: str = ""
    last_heartbeat: float = field(default_factory=time.time)
    data_channel: JsonSocket | None = None
    last_metrics: dict[str, Any] = field(default_factory=dict)
    last_task: str = ""


@dataclass
class WebVisitor:
    visitor_id: str
    ip_address: str
    label: str
    language: str
    hardware_threads: int
    device_memory_gb: float
    user_agent: str
    last_seen: float = field(default_factory=time.time)


class ManagerServer:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.log = configure_logging("pulsecheck.manager")
        self.fernet = build_fernet(config["fernet_key"])
        self.tasks = load_tasks(resolve_from_config(config, config["tasks_file"]))
        self.host = config["host"]
        self.handshake_port = int(config["handshake_port"])
        self.data_port = int(config["data_port"])
        self.alert_port = int(config["alert_port"])
        self.web_port = int(config.get("web_port", 5000))
        self.heartbeat_timeout = int(config["heartbeat_timeout_seconds"])
        self.task_interval = int(config["task_interval_seconds"])
        self.allowed_workers = {
            item["worker_id"]: item["ip"] for item in config.get("allowed_workers", [])
        }
        self.pending_tokens: dict[str, dict[str, str]] = {}
        self.sessions: dict[str, WorkerSession] = {}
        self.visitors: dict[str, WebVisitor] = {}
        self.recent_events: list[dict[str, str]] = []
        self.recent_alerts: list[dict[str, str]] = []
        self.lock = threading.Lock()

    def run(self) -> None:
        DashboardServer(
            host=self.host,
            port=self.web_port,
            snapshot_provider=self.dashboard_snapshot,
            visitor_recorder=self.record_visitor_checkin,
            logger=self.log,
        ).start()
        threading.Thread(target=self._run_alert_listener, daemon=True).start()
        threading.Thread(target=self._run_timeout_monitor, daemon=True).start()
        threading.Thread(target=self._run_data_server, daemon=True).start()
        self._run_handshake_server()

    def _run_handshake_server(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.handshake_port))
            server.listen()
            self.log.info("Handshake server listening on %s:%s", self.host, self.handshake_port)
            while True:
                conn, address = server.accept()
                threading.Thread(
                    target=self._handle_handshake,
                    args=(conn, address),
                    daemon=True,
                ).start()

    def _run_data_server(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.data_port))
            server.listen()
            self.log.info("Data server listening on %s:%s", self.host, self.data_port)
            while True:
                conn, address = server.accept()
                threading.Thread(
                    target=self._handle_data_channel,
                    args=(conn, address),
                    daemon=True,
                ).start()

    def _run_alert_listener(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
            server.bind((self.host, self.alert_port))
            self.log.info("Alert listener active on %s:%s", self.host, self.alert_port)
            while True:
                data, address = server.recvfrom(8192)
                try:
                    message = self.fernet.decrypt(data).decode("utf-8")
                except Exception as exc:  # noqa: BLE001
                    self.log.warning("Dropped invalid alert from %s: %s", address, exc)
                    continue
                self.log.warning("UDP alert from %s: %s", address[0], message)
                self._push_alert("UDP alert", f"{address[0]} sent {message}")

    def _run_timeout_monitor(self) -> None:
        while True:
            time.sleep(2)
            now = time.time()
            expired: list[str] = []
            with self.lock:
                for worker_id, session in self.sessions.items():
                    if now - session.last_heartbeat > self.heartbeat_timeout:
                        expired.append(worker_id)
                for worker_id in expired:
                    self.log.warning("Worker %s timed out after heartbeat loss", worker_id)
                    session = self.sessions.pop(worker_id)
                    if session.data_channel is not None:
                        session.data_channel.close()
                    self._push_event("Worker timeout", f"{worker_id} stopped sending heartbeats")

    def _handle_handshake(self, conn: socket.socket, address: tuple[str, int]) -> None:
        channel = JsonSocket(conn, self.fernet)
        try:
            payload = channel.recv()
            worker_id = payload.get("worker_id", "")
            if payload.get("type") != "auth":
                channel.send({"type": "auth_result", "status": "error", "reason": "invalid_type"})
                return
            if not self._is_allowed(worker_id, address[0]):
                channel.send({"type": "auth_result", "status": "error", "reason": "unauthorized"})
                self.log.warning("Rejected worker %s from %s", worker_id, address[0])
                self._push_event("Worker rejected", f"{worker_id} from {address[0]} was not allowed")
                return

            token = new_session_token()
            with self.lock:
                self.pending_tokens[worker_id] = {
                    "token": token,
                    "platform": str(payload.get("platform", "")),
                }
            channel.send(
                {
                    "type": "auth_result",
                    "status": "ok",
                    "worker_id": worker_id,
                    "session_token": token,
                    "data_port": self.data_port,
                    "alert_port": self.alert_port,
                }
            )
            self.log.info("Authenticated worker %s from %s", worker_id, address[0])
            self._push_event("Worker authenticated", f"{worker_id} authenticated from {address[0]}")
        except Exception as exc:  # noqa: BLE001
            self.log.error("Handshake error from %s: %s", address, exc)
        finally:
            channel.close()

    def _handle_data_channel(self, conn: socket.socket, address: tuple[str, int]) -> None:
        channel = JsonSocket(conn, self.fernet)
        worker_id = "unknown"
        try:
            payload = channel.recv()
            worker_id = payload.get("worker_id", "")
            token = payload.get("session_token", "")
            if payload.get("type") != "register_data":
                channel.send({"type": "register_result", "status": "error", "reason": "invalid_type"})
                return

            with self.lock:
                pending = self.pending_tokens.get(worker_id)
                if pending is None or pending.get("token") != token:
                    channel.send(
                        {"type": "register_result", "status": "error", "reason": "bad_session"}
                    )
                    return
                self.pending_tokens.pop(worker_id, None)
                session = WorkerSession(
                    worker_id=worker_id,
                    address=address,
                    session_token=token,
                    platform_name=pending.get("platform", ""),
                    data_channel=channel,
                )
                self.sessions[worker_id] = session

            channel.send({"type": "register_result", "status": "ok"})
            self.log.info("Worker %s opened data channel from %s", worker_id, address[0])
            self._push_event("Data channel ready", f"{worker_id} opened the encrypted TCP data channel")

            sender = threading.Thread(
                target=self._task_sender_loop,
                args=(worker_id, channel),
                daemon=True,
            )
            sender.start()

            while True:
                message = channel.recv()
                self._handle_worker_message(worker_id, message)
        except Exception as exc:  # noqa: BLE001
            self.log.warning("Data channel closed for %s: %s", worker_id, exc)
        finally:
            with self.lock:
                session = self.sessions.pop(worker_id, None)
            if session is not None and session.data_channel is not None:
                session.data_channel.close()
            if worker_id != "unknown":
                self._push_event("Worker disconnected", f"{worker_id} disconnected from the manager")

    def _task_sender_loop(self, worker_id: str, channel: JsonSocket) -> None:
        task_index = 0
        while True:
            with self.lock:
                session = self.sessions.get(worker_id)
                if session is None:
                    return
            task = self.tasks[task_index % len(self.tasks)]
            channel.send(
                {
                    "type": "task",
                    "worker_id": worker_id,
                    "action": task.action,
                    "argument": task.argument,
                }
            )
            self.log.info("Sent task %s to %s", self._format_task(task), worker_id)
            self._push_event("Task sent", f"{worker_id} received {self._format_task(task)}")
            task_index += 1
            time.sleep(self.task_interval)

    def _handle_worker_message(self, worker_id: str, message: dict[str, Any]) -> None:
        message_type = message.get("type")
        with self.lock:
            session = self.sessions.get(worker_id)
            if session is not None:
                session.last_heartbeat = time.time()

        if message_type == "heartbeat":
            self.log.info("Heartbeat from %s", worker_id)
            return
        if message_type == "metrics":
            with self.lock:
                session = self.sessions.get(worker_id)
                if session is not None:
                    session.last_metrics = {
                        "cpu_percent": float(message.get("cpu_percent", 0.0)),
                        "memory_percent": float(message.get("memory_percent", 0.0)),
                        "disk_percent": float(message.get("disk_percent", 0.0)),
                    }
            self.log.info(
                "Metrics from %s: CPU %.1f%% RAM %.1f%% Disk %.1f%%",
                worker_id,
                float(message.get("cpu_percent", 0.0)),
                float(message.get("memory_percent", 0.0)),
                float(message.get("disk_percent", 0.0)),
            )
            return
        if message_type == "task_result":
            with self.lock:
                session = self.sessions.get(worker_id)
                if session is not None:
                    session.last_task = str(message.get("output", ""))
            self.log.info(
                "Task result from %s for %s: %s",
                worker_id,
                message.get("action"),
                message.get("output", ""),
            )
            self._push_event(
                "Task result",
                f"{worker_id} completed {message.get('action')} with output: {message.get('output', '')}",
            )
            return
        self.log.info("Message from %s: %s", worker_id, message)

    def _is_allowed(self, worker_id: str, ip_address: str) -> bool:
        wildcard_ip = self.allowed_workers.get("*")
        if wildcard_ip in {"*", ip_address}:
            return True
        allowed_ip = self.allowed_workers.get(worker_id)
        if allowed_ip is None:
            return False
        return allowed_ip in {"*", ip_address}

    def record_visitor_checkin(self, payload: dict[str, Any], ip_address: str) -> None:
        visitor_id = str(payload.get("visitor_id", "")).strip() or f"visitor-{int(time.time())}"
        label = str(payload.get("label", "")).strip() or "Browser Visitor"
        visitor = WebVisitor(
            visitor_id=visitor_id,
            ip_address=ip_address,
            label=label,
            language=str(payload.get("language", "unknown")),
            hardware_threads=int(payload.get("hardware_threads", 0) or 0),
            device_memory_gb=float(payload.get("device_memory_gb", 0) or 0),
            user_agent=str(payload.get("user_agent", "unknown")),
            last_seen=time.time(),
        )
        with self.lock:
            is_new = visitor_id not in self.visitors
            self.visitors[visitor_id] = visitor
        if is_new:
            self._push_event("Web visitor joined", f"{label} joined from {ip_address}")

    def dashboard_snapshot(self) -> dict[str, Any]:
        now = time.time()
        with self.lock:
            workers = [
                {
                    "worker_id": session.worker_id,
                    "address": f"{session.address[0]}:{session.address[1]}",
                    "platform": session.platform_name or platform.system(),
                    "online": now - session.last_heartbeat <= self.heartbeat_timeout,
                    "last_heartbeat_age": self._format_age(now - session.last_heartbeat),
                    "metrics": {
                        "cpu_percent": session.last_metrics.get("cpu_percent"),
                        "memory_percent": session.last_metrics.get("memory_percent"),
                        "disk_percent": session.last_metrics.get("disk_percent"),
                    },
                    "last_task": session.last_task,
                }
                for session in self.sessions.values()
            ]
            visitors = [
                {
                    "visitor_id": visitor.visitor_id,
                    "ip_address": visitor.ip_address,
                    "label": visitor.label,
                    "language": visitor.language,
                    "hardware_threads": visitor.hardware_threads,
                    "device_memory_gb": visitor.device_memory_gb,
                    "last_seen_age": self._format_age(now - visitor.last_seen),
                }
                for visitor in self.visitors.values()
                if now - visitor.last_seen <= 120
            ]
            events = list(reversed(self.recent_events[-12:]))
            alerts = list(reversed(self.recent_alerts[-6:]))
        display_host = self._display_host()
        return {
            "manager_display_host": display_host,
            "handshake_port": self.handshake_port,
            "data_port": self.data_port,
            "alert_port": self.alert_port,
            "web_port": self.web_port,
            "socket_workers": workers,
            "web_visitors": visitors,
            "events": events,
            "alerts": alerts,
        }

    def _display_host(self) -> str:
        if self.host not in {"0.0.0.0", "::"}:
            return self.host
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            probe.connect(("8.8.8.8", 80))
            ip_address = probe.getsockname()[0]
            probe.close()
            return ip_address
        except OSError:
            return "127.0.0.1"

    def _push_event(self, title: str, message: str) -> None:
        event = {"title": title, "message": message, "time": time.strftime("%I:%M:%S %p")}
        with self.lock:
            self.recent_events.append(event)
            self.recent_events = self.recent_events[-40:]

    def _push_alert(self, title: str, message: str) -> None:
        alert = {"title": title, "message": message, "time": time.strftime("%I:%M:%S %p")}
        with self.lock:
            self.recent_alerts.append(alert)
            self.recent_alerts = self.recent_alerts[-20:]
            self.recent_events.append(alert)
            self.recent_events = self.recent_events[-40:]

    @staticmethod
    def _format_age(seconds: float) -> str:
        if seconds < 1:
            return "just now"
        if seconds < 60:
            return f"{int(seconds)}s ago"
        minutes = int(seconds // 60)
        if minutes < 60:
            return f"{minutes}m ago"
        hours = int(minutes // 60)
        return f"{hours}h ago"

    @staticmethod
    def _format_task(task: Task) -> str:
        if task.argument:
            return f"{task.action}:{task.argument}"
        return task.action


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PulseCheck manager.")
    default_config = runtime_root() / "config" / "manager.json"
    parser.add_argument("--config", default=str(default_config))
    args = parser.parse_args()
    config = load_json(args.config)
    ManagerServer(config).run()
