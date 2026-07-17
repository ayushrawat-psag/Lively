from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.email_verification import EmailVerificationCode
from app.models.user import User


class AuthRepository:
    """All database access goes through SQLAlchemy ORM models/sessions."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        return self.db.scalars(stmt).first()

    def get_user_by_id(self, user_id: UUID) -> User | None:
        return self.db.get(User, user_id)

    def create_user(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def save(self) -> None:
        self.db.commit()

    def refresh(self, instance: object) -> None:
        self.db.refresh(instance)

    def invalidate_active_codes(self, user_id: UUID) -> None:
        stmt = select(EmailVerificationCode).where(
            EmailVerificationCode.user_id == user_id,
            EmailVerificationCode.is_used.is_(False),
        )
        codes = self.db.scalars(stmt).all()
        now = datetime.now(timezone.utc)
        for verification in codes:
            verification.is_used = True
            verification.used_at = now
        if codes:
            self.db.flush()

    def create_verification_code(self, code: EmailVerificationCode) -> EmailVerificationCode:
        self.db.add(code)
        self.db.flush()
        return code

    def get_active_code(self, code: str) -> EmailVerificationCode | None:
        now = datetime.now(timezone.utc)
        stmt = (
            select(EmailVerificationCode)
            .where(
                EmailVerificationCode.code == code,
                EmailVerificationCode.is_used.is_(False),
                EmailVerificationCode.expires_at >= now,
            )
            .order_by(EmailVerificationCode.created_at.desc())
        )
        return self.db.scalars(stmt).first()

    def mark_code_used(self, verification: EmailVerificationCode) -> None:
        verification.is_used = True
        verification.used_at = datetime.now(timezone.utc)
        self.db.flush()

    def mark_email_verified(self, user: User) -> None:
        user.email_verified = True
        self.db.flush()

    def update_last_login(self, user: User) -> None:
        user.last_login_at = datetime.now(timezone.utc)
        self.db.flush()
