from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ContentStatus, SimulationType

if TYPE_CHECKING:
    from app.models.habit import Habit
    from app.models.island import Island
    from app.models.location import Location
    from app.models.prize_item import PrizeItem
    from app.models.simulation_answer import SimulationAnswer


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    island_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("islands.id"),
        nullable=False,
        index=True,
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id"),
        nullable=True,
        index=True,
    )
    simulation_name: Mapped[str] = mapped_column(String(200), nullable=False)
    activity_key: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    hero_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    simulation_type: Mapped[SimulationType] = mapped_column(
        Enum(SimulationType, name="simulation_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    question_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    correct_result_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    correct_result_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    wrong_result_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    wrong_result_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, name="content_status", create_constraint=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ContentStatus.ACTIVE,
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
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

    island: Mapped[Island] = relationship("Island", back_populates="simulations")
    location: Mapped[Location | None] = relationship("Location", back_populates="simulations")
    answers: Mapped[list[SimulationAnswer]] = relationship(
        "SimulationAnswer", back_populates="simulation"
    )
    prize_items: Mapped[list[PrizeItem]] = relationship("PrizeItem", back_populates="simulation")
    habits: Mapped[list[Habit]] = relationship("Habit", back_populates="simulation")
