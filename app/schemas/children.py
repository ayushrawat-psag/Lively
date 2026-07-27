from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class CreateChildRequest(BaseModel):
    name: str = Field(..., min_length=2)
    date_of_birth: date = Field(..., alias="dateOfBirth")
    gender: str = Field(..., min_length=1)
    devices: list[str] = Field(default_factory=list)
    pin: str = Field(..., min_length=4, max_length=4)

    model_config = {"populate_by_name": True}

    @field_validator("name")
    @classmethod
    def name_min_length(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Child name must be at least 2 characters")
        return cleaned

    @field_validator("pin")
    @classmethod
    def pin_must_be_digits(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 4:
            raise ValueError("PIN must be a 4-digit number")
        return value

    @field_validator("gender")
    @classmethod
    def gender_required(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("Gender is required")
        return cleaned


class UpdateChildRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2)
    date_of_birth: date | None = Field(default=None, alias="dateOfBirth")
    gender: str | None = None
    devices: list[str] | None = None
    pin: str | None = Field(default=None, min_length=4, max_length=4)

    model_config = {"populate_by_name": True}

    @field_validator("name")
    @classmethod
    def name_min_length(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Child name must be at least 2 characters")
        return cleaned

    @field_validator("pin")
    @classmethod
    def pin_must_be_digits(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.isdigit() or len(value) != 4:
            raise ValueError("PIN must be a 4-digit number")
        return value

    @field_validator("gender")
    @classmethod
    def normalize_gender(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("Gender is required")
        return cleaned


class ChildProgress(BaseModel):
    completed_activities: int = Field(0, alias="completedActivities")
    current_level: str | int | None = Field(default=None, alias="currentLevel")

    model_config = {"populate_by_name": True}


class UpdateChildAppStateRequest(BaseModel):
    onboarding: bool | None = Field(default=None, alias="onBoarding")
    child_app_tour: bool | None = Field(default=None, alias="childAppTour")

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def at_least_one_field(self) -> "UpdateChildAppStateRequest":
        if self.onboarding is None and self.child_app_tour is None:
            raise ValueError("At least one of onBoarding or childAppTour must be provided")
        return self


class ChildPublic(BaseModel):
    """List / patch child shape (no pin, no progress)."""

    id: UUID
    name: str
    date_of_birth: date = Field(..., alias="dateOfBirth")
    gender: str
    devices: list[str] = []
    onboarding: bool = Field(False, alias="onBoarding")
    child_app_tour: bool = Field(False, alias="childAppTour")

    model_config = {"populate_by_name": True}


class ChildCreatedPublic(ChildPublic):
    pin: str


class ChildDetailPublic(ChildPublic):
    progress: ChildProgress


class CreateChildResponse(BaseModel):
    success: bool
    message: str
    child: ChildCreatedPublic

    model_config = {"populate_by_name": True}


class ChildDetailResponse(BaseModel):
    success: bool
    message: str
    child: ChildDetailPublic

    model_config = {"populate_by_name": True}


class ChildUpdateResponse(BaseModel):
    success: bool
    message: str
    child: ChildPublic

    model_config = {"populate_by_name": True}


class ChildAppStateUpdateResponse(BaseModel):
    success: bool
    message: str
    child: ChildPublic

    model_config = {"populate_by_name": True}


class ChildrenListResponse(BaseModel):
    success: bool
    message: str
    children: list[ChildPublic]

    model_config = {"populate_by_name": True}


class DeleteChildResponse(BaseModel):
    success: bool
    message: str
    child_id: UUID = Field(..., alias="childId")

    model_config = {"populate_by_name": True}
