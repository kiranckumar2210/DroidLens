"""Password hashing and JWT token utilities."""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import bcrypt
import jwt

from inspectiq.auth.config import get_auth_config

JWT_SECRET = os.environ.get(
    "DROIDLENS_JWT_SECRET",
    os.environ.get("INSPECTIQ_JWT_SECRET", "droidlens-dev-secret-change-in-production"),
)
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: str) -> Tuple[str, int]:
    cfg = get_auth_config()
    expires_delta = timedelta(minutes=cfg.access_token_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": user_id,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": secrets.token_hex(8),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, int(expires_delta.total_seconds())


def create_refresh_token(user_id: str, remember_me: bool = False) -> Tuple[str, int, str]:
    cfg = get_auth_config()
    days = cfg.refresh_token_days_remember if remember_me else cfg.refresh_token_days
    expires_delta = timedelta(days=days)
    expire = datetime.now(timezone.utc) + expires_delta
    jti = secrets.token_hex(16)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": jti,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, int(expires_delta.total_seconds()), jti


def hash_refresh_token(token: str) -> str:
    return _hash_token(token)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") not in (None, "access"):
            return None
        return payload
    except jwt.PyJWTError:
        return None


def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except jwt.PyJWTError:
        return None


def create_token_pair(user_id: str, remember_me: bool = False) -> Tuple[str, int, str, int, str]:
    access, access_exp = create_access_token(user_id)
    refresh, refresh_exp, jti = create_refresh_token(user_id, remember_me)
    return access, access_exp, refresh, refresh_exp, jti
