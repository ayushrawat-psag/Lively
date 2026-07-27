from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import RewardType


class Reward(Base):
    __tablename__ = "rewards"
    __table_args__ = (CheckConstraint("stars_required > 0", name="ck_rewards_stars_required_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    reward_name: Mapped[str] = mapped_column(String(200), nullable=False)
    reward_type: Mapped[RewardType] = mapped_column(
        Enum(RewardType, name="reward_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    stars_required: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
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
