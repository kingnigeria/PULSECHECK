from __future__ import annotations

import secrets

from cryptography.fernet import Fernet


def build_fernet(key: str) -> Fernet:
    return Fernet(key.encode("ascii"))


def new_session_token() -> str:
    return secrets.token_urlsafe(24)
