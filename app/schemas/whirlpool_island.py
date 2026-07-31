from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_serializer


class ActivityProgressPublic(BaseModel):
    completed: bool
    attempts: int
    completed_at: datetime | None = Field(default=None, alias="completedAt")

    model_config = {"populate_by_name": True}



class ScriptAnswerPublic(BaseModel):
    id: str
    label: str
    is_correct: bool = Field(..., alias="isCorrect")

    model_config = {"populate_by_name": True}


class ResultPublic(BaseModel):
    title: str
    message: str | None = None

    model_config = {"populate_by_name": True}


class ScriptPublic(BaseModel):
    question: str
    answers: list[ScriptAnswerPublic]
    correct_result: ResultPublic = Field(..., alias="correctResult")
    wrong_result: ResultPublic = Field(..., alias="wrongResult")

    model_config = {"populate_by_name": True}


class HabitStepOptionPublic(BaseModel):
    id: str
    label: str

    model_config = {"populate_by_name": True}


class HabitStepPublic(BaseModel):
    id: str
    type: str
    question: str
    options: list[HabitStepOptionPublic]

    model_config = {"populate_by_name": True}


class HabitCorrectResultPublic(BaseModel):
    title: str

    model_config = {"populate_by_name": True}


class HabitPublic(BaseModel):
    description: str
    steps: list[HabitStepPublic]
    correct_result: HabitCorrectResultPublic = Field(..., alias="correctResult")

    model_config = {"populate_by_name": True}


class ActivityPublic(BaseModel):
    id: str
    type: str
    status: str
    title: str
    progress: ActivityProgressPublic
    script: ScriptPublic | None = None
    habit: HabitPublic | None = None

    model_config = {"populate_by_name": True}

    @model_serializer(mode="wrap")
    def _serialize(self, serializer) -> dict[str, Any]:
        data = serializer(self)
        if data.get("script") is None:
            data.pop("script", None)
        if data.get("habit") is None:
            data.pop("habit", None)
        return data



class IslandStatusPublic(BaseModel):
    completed: bool
    completed_at: datetime | None = Field(default=None, alias="completedAt")

    model_config = {"populate_by_name": True}


class WhirlpoolIslandData(BaseModel):
    island: IslandStatusPublic
    activities: list[ActivityPublic]

    model_config = {"populate_by_name": True}


class WhirlpoolIslandDetailsResponse(BaseModel):
    success: bool
    message: str
    data: WhirlpoolIslandData

    model_config = {"populate_by_name": True}


class CompleteActivityRequest(BaseModel):
    completed: bool
    attempts: int | None = None

    model_config = {"populate_by_name": True}


class CompleteActivityData(BaseModel):
    activity_id: str = Field(..., alias="activityId")
    child_id: str = Field(..., alias="childId")
    activity_type: str = Field(..., alias="activityType")
    is_correct: bool = Field(..., alias="isCorrect")
    progress: ActivityProgressPublic

    model_config = {"populate_by_name": True}


class CompleteActivityResponse(BaseModel):
    success: bool
    message: str
    data: CompleteActivityData

    model_config = {"populate_by_name": True}


class CompleteIslandRequest(BaseModel):
    completed: bool

    model_config = {"populate_by_name": True}


class CompleteIslandData(BaseModel):
    child_id: str = Field(..., alias="childId")
    island: IslandStatusPublic

    model_config = {"populate_by_name": True}


class CompleteIslandResponse(BaseModel):
    success: bool
    message: str
    data: CompleteIslandData

    model_config = {"populate_by_name": True}
