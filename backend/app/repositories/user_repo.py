import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.models import AuditLog, RefreshToken, User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower()))

    def create(self, email: str, password_hash: str, full_name: str) -> User:
        user = User(email=email.lower(), password_hash=password_hash, full_name=full_name)
        self.db.add(user)
        self.db.flush()
        return user


class RefreshTokenRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(
        self, user_id: uuid.UUID, token_hash: str, family_id: uuid.UUID, expires_at: datetime
    ) -> RefreshToken:
        row = RefreshToken(
            user_id=user_id, token_hash=token_hash, family_id=family_id, expires_at=expires_at
        )
        self.db.add(row)
        self.db.flush()
        return row

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    def revoke(self, row: RefreshToken) -> None:
        row.revoked_at = utcnow()

    def revoke_family(self, family_id: uuid.UUID) -> None:
        self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )


class AuditLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self, action: str, user_id: uuid.UUID | None, ip: str | None, detail: dict | None = None
    ) -> None:
        self.db.add(AuditLog(action=action, user_id=user_id, ip=ip, detail=detail or {}))
