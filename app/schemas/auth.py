from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=6)
    guardian: bool
    accepted_terms: bool = Field(..., alias="acceptedTerms")

    model_config = {"populate_by_name": True}

    @field_validator("guardian")
    @classmethod
    def guardian_must_be_true(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Guardian confirmation is required")
        return value

    @field_validator("accepted_terms")
    @classmethod
    def terms_must_be_accepted(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Terms must be accepted")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=1)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class UserPublic(BaseModel):
    id: UUID | int | str
    name: str
    email: str
    guardian: bool
    email_verified: bool = Field(..., alias="emailVerified")

    model_config = {"populate_by_name": True, "from_attributes": True}


class ChildPublic(BaseModel):
    id: UUID | int | str
    name: str
    initial: str


class SignupResponse(BaseModel):
    success: bool
    message: str
    email_exists: bool = Field(..., alias="emailExists")
    email_verification_required: bool = Field(..., alias="emailVerificationRequired")
    user: UserPublic
    verification_code: str | None = Field(default=None, alias="verificationCode")

    model_config = {"populate_by_name": True}


class LoginResponse(BaseModel):
    success: bool
    message: str
    token: str
    user: UserPublic
    children: list[ChildPublic] = []

    model_config = {"populate_by_name": True}


class VerifyEmailResponse(BaseModel):
    success: bool
    message: str
    code: str
    token: str
    user: UserPublic
    children: list[ChildPublic] = []

    model_config = {"populate_by_name": True}


class ResendVerificationResponse(BaseModel):
    success: bool
    message: str
    verification_code: str | None = Field(default=None, alias="verificationCode")

    model_config = {"populate_by_name": True}


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    email_exists: bool | None = Field(default=None, alias="emailExists")
    email_verified: bool | None = Field(default=None, alias="emailVerified")

    model_config = {"populate_by_name": True}


def split_full_name(name: str) -> tuple[str, str]:
    parts = name.strip().split(None, 1)
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def user_to_public(user: Any) -> UserPublic:
    return UserPublic(
        id=user.id,
        name=user.full_name,
        email=user.email or "",
        guardian=user.is_guardian,
        emailVerified=user.email_verified,
    )
