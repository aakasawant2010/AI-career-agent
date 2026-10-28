import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import utcnow
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.models import User
from app.repositories.user_repo import AuditLogRepository, RefreshTokenRepository, UserRepository
from app.schemas.auth import TokenPair

log = logging.getLogger(__name__)

# Verified against when the email is unknown so login timing doesn't reveal which emails exist.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


class AuthError(Exception):
    """Base for expected auth failures; the API maps these to HTTP errors."""


class EmailAlreadyRegistered(AuthError):
    pass


class InvalidCredentials(AuthError):
    pass


class InvalidRefreshToken(AuthError):
    pass


def _aware(dt: datetime) -> datetime:
    # SQLite drops tzinfo on read; treat stored values as UTC.
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.tokens = RefreshTokenRepository(db)
        self.audit = AuditLogRepository(db)

    def register(self, email: str, password: str, full_name: str, ip: str | None) -> User:
        if self.users.get_by_email(email):
            raise EmailAlreadyRegistered()
        try:
            user = self.users.create(email, hash_password(password), full_name.strip())
            self.audit.record("auth.register", user.id, ip)
            self.db.commit()
        except IntegrityError:  # lost a race with a concurrent registration
            self.db.rollback()
            raise EmailAlreadyRegistered() from None
        return user

    def login(self, email: str, password: str, ip: str | None) -> TokenPair:
        user = self.users.get_by_email(email)
        ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
        if not user or not ok or not user.is_active:
            self.audit.record("auth.login_failed", user.id if user else None, ip)
            self.db.commit()
            raise InvalidCredentials()
        pair = self._issue_pair(user.id, family_id=uuid.uuid4())
        self.audit.record("auth.login", user.id, ip)
        self.db.commit()
        return pair

    def refresh(self, refresh_token: str, ip: str | None) -> TokenPair:
        row = self.tokens.get_by_hash(hash_refresh_token(refresh_token))
        if row is None:
            raise InvalidRefreshToken()
        if row.revoked_at is not None:
            # A rotated-out token was presented again: assume theft, kill the family.
            self.tokens.revoke_family(row.family_id)
            self.audit.record("auth.refresh_reuse_detected", row.user_id, ip)
            self.db.commit()
            raise InvalidRefreshToken()
        if _aware(row.expires_at) <= utcnow():
            raise InvalidRefreshToken()
        user = self.users.get(row.user_id)
        if not user or not user.is_active:
            raise InvalidRefreshToken()
        self.tokens.revoke(row)
        pair = self._issue_pair(user.id, family_id=row.family_id)
        self.audit.record("auth.refresh", user.id, ip)
        self.db.commit()
        return pair

    def logout(self, refresh_token: str, ip: str | None) -> None:
        row = self.tokens.get_by_hash(hash_refresh_token(refresh_token))
        if row is not None:
            self.tokens.revoke_family(row.family_id)
            self.audit.record("auth.logout", row.user_id, ip)
            self.db.commit()

    def _issue_pair(self, user_id: uuid.UUID, family_id: uuid.UUID) -> TokenPair:
        s = get_settings()
        raw, hashed = new_refresh_token()
        self.tokens.add(user_id, hashed, family_id, utcnow() + timedelta(days=s.refresh_token_days))
        return TokenPair(access_token=create_access_token(user_id), refresh_token=raw)
