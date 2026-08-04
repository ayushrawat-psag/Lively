from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.habit_tracker import FridgeInventoryQuantities


class FridgeHabitInventoryPublic(BaseModel):
    habit_id: str = Field(..., alias="habitId")
    inventory: FridgeInventoryQuantities

    model_config = {"populate_by_name": True}


class FridgeInventoryAllData(BaseModel):
    child_id: str = Field(..., alias="childId")
    habits: list[FridgeHabitInventoryPublic]
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = {"populate_by_name": True}


class FridgeInventoryAllResponse(BaseModel):
    success: bool
    message: str
    data: FridgeInventoryAllData

    model_config = {"populate_by_name": True}


class FridgeInventoryOneData(BaseModel):
    child_id: str = Field(..., alias="childId")
    habit_id: str = Field(..., alias="habitId")
    inventory: FridgeInventoryQuantities
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = {"populate_by_name": True}


class FridgeInventoryOneResponse(BaseModel):
    success: bool
    message: str
    data: FridgeInventoryOneData

    model_config = {"populate_by_name": True}


class ConsumeFridgeRequest(BaseModel):
    reward_icon: str = Field(..., alias="rewardIcon")
    quantity: int

    model_config = {"populate_by_name": True}

    @field_validator("reward_icon")
    @classmethod
    def validate_icon(cls, value: str) -> str:
        allowed = {"fries", "mussels", "sardini"}
        if value not in allowed:
            raise ValueError("rewardIcon must be fries, mussels, or sardini")
        return value

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value: int) -> int:
        if value < 1:
            raise ValueError("quantity must be a positive integer")
        return value


class ConsumedInfo(BaseModel):
    reward_icon: str = Field(..., alias="rewardIcon")
    quantity: int

    model_config = {"populate_by_name": True}


class ConsumeFridgeData(BaseModel):
    child_id: str = Field(..., alias="childId")
    habit_id: str = Field(..., alias="habitId")
    consumed: ConsumedInfo
    inventory: FridgeInventoryQuantities
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = {"populate_by_name": True}


class ConsumeFridgeResponse(BaseModel):
    success: bool
    message: str
    data: ConsumeFridgeData

    model_config = {"populate_by_name": True}
