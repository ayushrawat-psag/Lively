from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.invite_code import generate_invite_code
from app.models.family import Family


class FamilyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_parent_user_id(self, parent_user_id: UUID) -> Family | None:
        stmt = select(Family).where(
            or_(
                Family.primary_parent_user_id == parent_user_id,
                Family.secondary_parent_user_id == parent_user_id,
            )
        )
        return self.db.scalars(stmt).first()

    def create(self, family: Family) -> Family:
        self.db.add(family)
        self.db.flush()
        return family

    def save(self) -> None:
        self.db.commit()

    def flush(self) -> None:
        self.db.flush()

    def _generate_invite_code(self) -> str:
        for _ in range(10):
            code = generate_invite_code()
            exists = self.db.scalar(select(func.count()).select_from(Family).where(Family.invite_code == code))
            if not exists:
                return code
        raise RuntimeError("Failed to generate unique family invite code")

    def ensure_for_parent(self, parent_user_id: UUID) -> Family:
        existing = self.get_by_parent_user_id(parent_user_id)
        if existing:
            return existing

        family = Family(
            primary_parent_user_id=parent_user_id,
            invite_code=self._generate_invite_code(),
        )
        self.create(family)
        return family
