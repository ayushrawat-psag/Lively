from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class HabitTrackerStepPublic(BaseModel):
    step_id: str = Field(..., alias="stepId")
    order: int
    image: str | None = None
    text: str
    button_text: str = Field(..., alias="buttonText")

    model_config = {"populate_by_name": True}


class HabitTrackerActivityPublic(BaseModel):
    activity_id: str = Field(..., alias="activityId")
    title: str
    is_active: bool = Field(..., alias="isActive")
    steps: list[HabitTrackerStepPublic]

    model_config = {"populate_by_name": True}


class HabitTrackerHabitCatalogItemPublic(BaseModel):
    habit_id: str = Field(..., alias="habitId")
    title: str
    is_active: bool = Field(..., alias="isActive")
    card_color: str | None = Field(default=None, alias="cardColor")
    default_activity_id: str = Field(..., alias="defaultActivityId")
    activities: dict[str, HabitTrackerActivityPublic]

    model_config = {"populate_by_name": True}


class HabitTrackerChildHabitPublic(BaseModel):
    habit_id: str = Field(..., alias="habitId")
    completed_dates: list[date] = Field(..., alias="completedDates")

    model_config = {"populate_by_name": True}


class HabitTrackerChildPublic(BaseModel):
    child_id: str = Field(..., alias="childId")
    habits: list[HabitTrackerChildHabitPublic]

    model_config = {"populate_by_name": True}


class HabitTrackerPayloadPublic(BaseModel):
    habit_catalog: dict[str, HabitTrackerHabitCatalogItemPublic] = Field(..., alias="habitCatalog")
    child: HabitTrackerChildPublic

    model_config = {"populate_by_name": True}


class HabitTrackerDetailsData(BaseModel):
    habit_tracker: HabitTrackerPayloadPublic = Field(..., alias="habitTracker")

    model_config = {"populate_by_name": True}


class HabitTrackerDetailsResponse(BaseModel):
    success: bool
    message: str
    data: HabitTrackerDetailsData

    model_config = {"populate_by_name": True}


class CompleteHabitRequest(BaseModel):
    habit_id: str = Field(..., alias="habitId")
    default_activity_id: str = Field(..., alias="defaultActivityId")
    date: date

    model_config = {"populate_by_name": True}


class CompleteHabitData(BaseModel):
    habit_id: str = Field(..., alias="habitId")
    default_activity_id: str = Field(..., alias="defaultActivityId")
    completed_dates: list[date] = Field(..., alias="completedDates")

    model_config = {"populate_by_name": True}


class CompleteHabitResponse(BaseModel):
    success: bool
    message: str
    data: CompleteHabitData

    model_config = {"populate_by_name": True}
