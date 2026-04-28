from __future__ import annotations

import argparse
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


@dataclass
class WorkerSession:
    worker_id: str
    address: tuple[str, int]
    session_token: str
    last_heartbeat: float = field(default_factory=time.time)
    data_channel: JsonSocket | None = None


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
        self.heartbeat_timeout = int(config["heartbeat_timeout_seconds"])
        self.task_interval = int(config["task_interval_seconds"])
        self.allowed_workers = {
            item["worker_id"]: item["ip"] for item in config.get("allowed_workers", [])
        }
        self.pending_tokens: dict[str, str] = {}
        self.sessions: dict[str, WorkerSession] = {}
        self.lock = threading.Lock()

    def run(self) -> None:
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
                return

            token = new_session_token()
            with self.lock:
                self.pending_tokens[worker_id] = token
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
                expected = self.pending_tokens.get(worker_id)
                if expected != token:
                    channel.send(
                        {"type": "register_result", "status": "error", "reason": "bad_session"}
                    )
                    return
                self.pending_tokens.pop(worker_id, None)
                session = WorkerSession(
                    worker_id=worker_id,
                    address=address,
                    session_token=token,
                    data_channel=channel,
                )
                self.sessions[worker_id] = session

            channel.send({"type": "register_result", "status": "ok"})
            self.log.info("Worker %s opened data channel from %s", worker_id, address[0])

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
            self.log.info(
                "Metrics from %s: CPU %.1f%% RAM %.1f%% Disk %.1f%%",
                worker_id,
                float(message.get("cpu_percent", 0.0)),
                float(message.get("memory_percent", 0.0)),
                float(message.get("disk_percent", 0.0)),
            )
            return
        if message_type == "task_result":
            self.log.info(
                "Task result from %s for %s: %s",
                worker_id,
                message.get("action"),
                message.get("output", ""),
            )
            return
        self.log.info("Message from %s: %s", worker_id, message)

    def _is_allowed(self, worker_id: str, ip_address: str) -> bool:
        allowed_ip = self.allowed_workers.get(worker_id)
        if allowed_ip is None:
            return False
        return allowed_ip in {"*", ip_address}

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
