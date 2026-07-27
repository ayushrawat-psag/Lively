from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import UserRewardEntryType


class UserReward(Base):
    __tablename__ = "user_rewards"
    __table_args__ = (
        Index(
            "uq_user_rewards_user_prize_item",
            "user_id",
            "prize_item_id",
            unique=True,
            postgresql_where="prize_item_id IS NOT NULL",
        ),
        Index("ix_user_rewards_user_occurred_at", "user_id", "occurred_at"),
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
    entry_type: Mapped[UserRewardEntryType] = mapped_column(
        Enum(UserRewardEntryType, name="user_reward_entry_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    habit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("habits.id"),
        nullable=True,
        index=True,
    )
    reward_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rewards.id"),
        nullable=True,
        index=True,
    )
    prize_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prize_items.id"),
        nullable=True,
        index=True,
    )
    stars_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
