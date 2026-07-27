from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import HabitTrackerStatus


class HabitTracker(Base):
    __tablename__ = "habit_tracker"
    __table_args__ = (
        UniqueConstraint("user_id", "habit_id", "tracking_date", name="uq_habit_tracker_user_habit_date"),
        Index("ix_habit_tracker_user_tracking_date", "user_id", "tracking_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
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
    tracking_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[HabitTrackerStatus] = mapped_column(
        Enum(HabitTrackerStatus, name="habit_tracker_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    evidence_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
