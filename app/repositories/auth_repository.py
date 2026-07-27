from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import UserType
from app.models.family import Family
from app.models.user import User
from app.models.user_activity import UserActivity


class AuthRepository:
    """All database access goes through SQLAlchemy ORM models/sessions."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        return self.db.scalars(stmt).first()

    def get_user_by_id(self, user_id: UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_user_by_invite_code(self, invite_code: str) -> User | None:
        stmt = select(User).where(User.invite_code == invite_code)
        return self.db.scalars(stmt).first()

    def create_user(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def save(self) -> None:
        self.db.commit()

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, instance: object) -> None:
        self.db.refresh(instance)

    def invalidate_active_codes(self, user_id: UUID) -> None:
        from app.models.email_verification import EmailVerificationCode

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

    def create_verification_code(self, code) -> object:
        self.db.add(code)
        self.db.flush()
        return code

    def get_active_code(self, *, user_id: UUID, code: str):
        from app.models.email_verification import EmailVerificationCode

        now = datetime.now(timezone.utc)
        stmt = (
            select(EmailVerificationCode)
            .where(
                EmailVerificationCode.user_id == user_id,
                EmailVerificationCode.code == code,
                EmailVerificationCode.is_used.is_(False),
                EmailVerificationCode.expires_at >= now,
            )
            .order_by(EmailVerificationCode.created_at.desc())
        )
        return self.db.scalars(stmt).first()

    def mark_code_used(self, verification) -> None:
        verification.is_used = True
        verification.used_at = datetime.now(timezone.utc)
        self.db.flush()

    def mark_email_verified(self, user: User) -> None:
        user.email_verified = True
        self.db.flush()

    def update_last_login(self, user: User) -> None:
        now = datetime.now(timezone.utc)
        activity = self.db.scalar(select(UserActivity).where(UserActivity.user_id == user.id))
        if activity is None:
            activity = UserActivity(user_id=user.id, last_login_at=now)
            self.db.add(activity)
        else:
            activity.last_login_at = now
        self.db.flush()

    def set_invite_code(self, user: User, invite_code: str) -> None:
        user.invite_code = invite_code
        self.db.flush()

    @staticmethod
    def _parent_family_filter(parent_user_id: UUID):
        return or_(
            Family.primary_parent_user_id == parent_user_id,
            Family.secondary_parent_user_id == parent_user_id,
        )

    def list_child_users_for_parent(self, parent_user_id: UUID) -> list[User]:
        stmt = (
            select(User)
            .join(Family, User.family_id == Family.id)
            .where(
                self._parent_family_filter(parent_user_id),
                User.user_type == UserType.CHILD,
                User.is_child.is_(True),
                User.deleted_at.is_(None),
            )
            .order_by(User.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())
