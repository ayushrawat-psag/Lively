from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChildHabitFridgeInventory(Base):
    __tablename__ = "child_habit_fridge_inventory"
    __table_args__ = (
        UniqueConstraint(
            "child_user_id",
            "habit_id",
            name="uq_child_habit_fridge_inventory_child_habit",
        ),
        Index("ix_child_habit_fridge_inventory_child_habit", "child_user_id", "habit_id"),
        CheckConstraint("fries >= 0 AND fries <= 9", name="ck_child_habit_fridge_fries_range"),
        CheckConstraint(
            "mussels >= 0 AND mussels <= 9",
            name="ck_child_habit_fridge_mussels_range",
        ),
        CheckConstraint(
            "sardini >= 0 AND sardini <= 9",
            name="ck_child_habit_fridge_sardini_range",
        ),
        CheckConstraint("current_streak >= 0", name="ck_child_habit_fridge_streak_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    child_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    habit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("habits.id"),
        nullable=False,
        index=True,
    )
    fries: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    mussels: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    sardini: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    current_streak: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    last_completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
