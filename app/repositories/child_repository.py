from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import UserType
from app.models.family import Family
from app.models.user import User


class ChildRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _parent_family_filter(parent_user_id: UUID):
        return or_(
            Family.primary_parent_user_id == parent_user_id,
            Family.secondary_parent_user_id == parent_user_id,
        )

    def create(self, child: User) -> User:
        self.db.add(child)
        self.db.flush()
        return child

    def save(self) -> None:
        self.db.commit()

    def refresh(self, child: User) -> None:
        self.db.refresh(child)

    def count_active_for_parent(self, parent_user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(User)
            .join(Family, User.family_id == Family.id)
            .where(
                self._parent_family_filter(parent_user_id),
                User.user_type == UserType.CHILD,
                User.is_child.is_(True),
                User.deleted_at.is_(None),
            )
        )
        return int(self.db.scalar(stmt) or 0)

    def list_active_for_parent(self, parent_user_id: UUID) -> list[User]:
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

    def get_active_for_parent(self, *, child_id: UUID, parent_user_id: UUID) -> User | None:
        stmt = (
            select(User)
            .join(Family, User.family_id == Family.id)
            .where(
                User.id == child_id,
                self._parent_family_filter(parent_user_id),
                User.user_type == UserType.CHILD,
                User.is_child.is_(True),
                User.deleted_at.is_(None),
            )
        )
        return self.db.scalars(stmt).first()

    def get_active_by_id(self, child_id: UUID) -> User | None:
        stmt = select(User).where(
            User.id == child_id,
            User.user_type == UserType.CHILD,
            User.is_child.is_(True),
            User.deleted_at.is_(None),
        )
        return self.db.scalars(stmt).first()

    def get_parent_user_id(self, child: User) -> UUID | None:
        if child.family_id is None:
            return None
        family = self.db.get(Family, child.family_id)
        if family is None:
            return None
        return family.primary_parent_user_id

    def soft_delete(self, child: User) -> None:
        child.deleted_at = datetime.now(timezone.utc)
        self.db.flush()
