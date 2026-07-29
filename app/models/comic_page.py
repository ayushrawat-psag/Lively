from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ContentStatus

if TYPE_CHECKING:
    from app.models.island import Island


class ComicPage(Base):
    __tablename__ = "comic_pages"
    __table_args__ = (
        UniqueConstraint("island_id", "display_order", name="uq_comic_pages_island_display_order"),
        CheckConstraint("display_order > 0", name="ck_comic_pages_display_order_positive"),
    )

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
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
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

    island: Mapped[Island] = relationship("Island", back_populates="comic_pages")
