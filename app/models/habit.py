from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ContentStatus, HabitType

if TYPE_CHECKING:
    from app.models.simulation import Simulation


class Habit(Base):
    __tablename__ = "habits"
    __table_args__ = (CheckConstraint("stars_to_earn >= 0", name="ck_habits_stars_to_earn_nonneg"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    simulation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("simulations.id"),
        nullable=False,
        index=True,
    )
    header_text: Mapped[str] = mapped_column(String(200), nullable=False)
    header_icon_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    stars_to_earn: Mapped[int] = mapped_column(Integer, nullable=False)
    habit_type: Mapped[HabitType] = mapped_column(
        Enum(HabitType, name="habit_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, name="content_status", create_constraint=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ContentStatus.ACTIVE,
    )
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

    simulation: Mapped[Simulation] = relationship("Simulation", back_populates="habits")
