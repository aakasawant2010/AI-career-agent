import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings


def hash_password(password: str) -> str:
    # bcrypt only uses the first 72 bytes; reject rather than silently truncate.
    raw = password.encode("utf-8")
    if len(raw) > 72:
        raise ValueError("password too long (max 72 bytes)")
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: uuid.UUID) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=s.access_token_minutes),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> uuid.UUID:
    """Return the user id or raise jwt.PyJWTError / ValueError."""
    s = get_settings()
    payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    if payload.get("type") != "access":
        raise ValueError("wrong token type")
    return uuid.UUID(payload["sub"])


def new_refresh_token() -> tuple[str, str]:
    """Return (opaque token for the client, sha256 hash to store)."""
    token = secrets.token_urlsafe(48)
    return token, hash_refresh_token(token)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
