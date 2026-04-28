from __future__ import annotations

import json
import socket
from typing import Any

from cryptography.fernet import Fernet


class JsonSocket:
    def __init__(self, sock: socket.socket, fernet: Fernet | None = None) -> None:
        self.sock = sock
        self.fernet = fernet
        self.reader = sock.makefile("rb")
        self.writer = sock.makefile("wb")

    def send(self, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload).encode("utf-8")
        if self.fernet is not None:
            raw = self.fernet.encrypt(raw)
        self.writer.write(raw + b"\n")
        self.writer.flush()

    def recv(self) -> dict[str, Any]:
        line = self.reader.readline()
        if not line:
            raise ConnectionError("socket closed")
        raw = line.rstrip(b"\r\n")
        if self.fernet is not None:
            raw = self.fernet.decrypt(raw)
        return json.loads(raw.decode("utf-8"))

    def close(self) -> None:
        try:
            self.reader.close()
        finally:
            try:
                self.writer.close()
            finally:
                self.sock.close()
