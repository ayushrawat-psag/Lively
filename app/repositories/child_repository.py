from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.child import Child


class ChildRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, child: Child) -> Child:
        self.db.add(child)
        self.db.flush()
        return child

    def save(self) -> None:
        self.db.commit()

    def refresh(self, child: Child) -> None:
        self.db.refresh(child)

    def count_active_for_parent(self, parent_user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Child)
            .where(
                Child.parent_user_id == parent_user_id,
                Child.deleted_at.is_(None),
            )
        )
        return int(self.db.scalar(stmt) or 0)

    def list_active_for_parent(self, parent_user_id: UUID) -> list[Child]:
        stmt = (
            select(Child)
            .where(
                Child.parent_user_id == parent_user_id,
                Child.deleted_at.is_(None),
            )
            .order_by(Child.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_active_for_parent(self, *, child_id: UUID, parent_user_id: UUID) -> Child | None:
        stmt = select(Child).where(
            Child.id == child_id,
            Child.parent_user_id == parent_user_id,
            Child.deleted_at.is_(None),
        )
        return self.db.scalars(stmt).first()

    def soft_delete(self, child: Child) -> None:
        child.deleted_at = datetime.now(timezone.utc)
        self.db.flush()
