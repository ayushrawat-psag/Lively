from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.email_verification import EmailVerificationCode


class UserType(str, enum.Enum):
    PARENT = "Parent"
    CHILD = "Child"
    TEACHER = "Teacher"
    GUARDIAN = "Guardian"


class AgeCohort(str, enum.Enum):
    TODDLER = "Toddler"
    CHILD = "Child"
    TWEEN = "Tween"
    TEEN = "Teen"
    ADULT = "Adult"


class UserStatus(str, enum.Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    SUSPENDED = "Suspended"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_type: Mapped[UserType] = mapped_column(
        Enum(UserType, name="user_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserType.PARENT,
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    pin_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    age_cohort: Mapped[AgeCohort | None] = mapped_column(
        Enum(AgeCohort, name="age_cohort", values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    is_child: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    invite_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    family_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    school_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    classroom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserStatus.ACTIVE,
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    accepted_terms: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
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

    email_verification_codes: Mapped[list[EmailVerificationCode]] = relationship(
        "EmailVerificationCode",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_guardian(self) -> bool:
        return self.user_type in (UserType.PARENT, UserType.GUARDIAN)
