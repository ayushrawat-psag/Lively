from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.simulation import Simulation


class SimulationAnswer(Base):
    __tablename__ = "simulation_answers"
    __table_args__ = (
        UniqueConstraint("simulation_id", "option_number", name="uq_simulation_answers_simulation_option"),
        UniqueConstraint("simulation_id", "answer_key", name="uq_simulation_answers_simulation_answer_key"),
    )

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
    option_number: Mapped[int] = mapped_column(Integer, nullable=False)
    answer_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
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

    simulation: Mapped[Simulation] = relationship("Simulation", back_populates="answers")
