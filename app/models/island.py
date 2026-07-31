from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ContentStatus

if TYPE_CHECKING:
    from app.models.comic_page import ComicPage
    from app.models.location import Location
    from app.models.simulation import Simulation
    from app.models.user import User


class Island(Base):
    __tablename__ = "islands"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    island_name: Mapped[str] = mapped_column(String(150), nullable=False)
    badge_icon_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, name="content_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ContentStatus.ACTIVE,
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    comic_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        unique=True,
        server_default=func.nextval("islands_comic_number_seq"),
    )
    images_per_page: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
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

    locations: Mapped[list[Location]] = relationship("Location", back_populates="island")
    simulations: Mapped[list[Simulation]] = relationship("Simulation", back_populates="island")
    comic_pages: Mapped[list[ComicPage]] = relationship("ComicPage", back_populates="island")
