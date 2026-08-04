from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.habit_tracker_repository import HabitTrackerRepository
from app.schemas.fridge_inventory import (
    ConsumeFridgeData,
    ConsumeFridgeRequest,
    ConsumeFridgeResponse,
    ConsumedInfo,
    FridgeHabitInventoryPublic,
    FridgeInventoryAllData,
    FridgeInventoryAllResponse,
    FridgeInventoryOneData,
    FridgeInventoryOneResponse,
)
from app.schemas.habit_tracker import FridgeInventoryQuantities


class FridgeInventoryService:
    def __init__(self, db: Session) -> None:
        self.repo = HabitTrackerRepository(db)
        self.db = db

    def get_all(self, child: User) -> FridgeInventoryAllResponse:
        habits = self.repo.list_active_habits()
        habit_ids = [h.id for h in habits]
        fridge_rows = {
            row.habit_id: row
            for row in self.repo.list_fridge_rows(child_user_id=child.id, habit_ids=habit_ids)
        }

        items: list[FridgeHabitInventoryPublic] = []
        latest: datetime | None = None
        for habit in habits:
            if not habit.habit_key:
                continue
            row = fridge_rows.get(habit.id)
            inventory = FridgeInventoryQuantities(
                fries=row.fries if row else 0,
                mussels=row.mussels if row else 0,
                sardini=row.sardini if row else 0,
            )
            if row and row.updated_at and (latest is None or row.updated_at > latest):
                latest = row.updated_at
            items.append(
                FridgeHabitInventoryPublic(
                    habitId=habit.habit_key,
                    inventory=inventory,
                )
            )

        return FridgeInventoryAllResponse(
            success=True,
            message="Fridge inventory fetched successfully",
            data=FridgeInventoryAllData(
                childId=str(child.id),
                habits=items,
                updatedAt=latest or datetime.now(timezone.utc),
            ),
        )

    def get_one(self, child: User, habit_key: str) -> FridgeInventoryOneResponse:
        habit = self.repo.get_habit_by_key(habit_key)
        if habit is None or not habit.habit_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "message": "Habit not found"},
            )
        row = self.repo.get_or_create_fridge(child_user_id=child.id, habit_id=habit.id)
        self.db.commit()
        self.db.refresh(row)

        return FridgeInventoryOneResponse(
            success=True,
            message="Fridge inventory fetched successfully",
            data=FridgeInventoryOneData(
                childId=str(child.id),
                habitId=habit.habit_key,
                inventory=FridgeInventoryQuantities(
                    fries=row.fries,
                    mussels=row.mussels,
                    sardini=row.sardini,
                ),
                updatedAt=row.updated_at or datetime.now(timezone.utc),
            ),
        )

    def consume(
        self,
        child: User,
        habit_key: str,
        payload: ConsumeFridgeRequest,
    ) -> ConsumeFridgeResponse:
        habit = self.repo.get_habit_by_key(habit_key)
        if habit is None or not habit.habit_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "message": "Habit not found"},
            )

        row = self.repo.get_or_create_fridge(child_user_id=child.id, habit_id=habit.id)
        available = getattr(row, payload.reward_icon)
        if available < payload.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "success": False,
                    "error": {
                        "code": "INSUFFICIENT_INVENTORY",
                        "message": "The requested quantity is not available.",
                        "details": {
                            "rewardIcon": payload.reward_icon,
                            "requestedQuantity": payload.quantity,
                            "availableQuantity": available,
                        },
                    },
                },
            )

        setattr(row, payload.reward_icon, available - payload.quantity)
        self.db.commit()
        self.db.refresh(row)

        return ConsumeFridgeResponse(
            success=True,
            message="Inventory consumed successfully",
            data=ConsumeFridgeData(
                childId=str(child.id),
                habitId=habit.habit_key,
                consumed=ConsumedInfo(
                    rewardIcon=payload.reward_icon,
                    quantity=payload.quantity,
                ),
                inventory=FridgeInventoryQuantities(
                    fries=row.fries,
                    mussels=row.mussels,
                    sardini=row.sardini,
                ),
                updatedAt=row.updated_at or datetime.now(timezone.utc),
            ),
        )
