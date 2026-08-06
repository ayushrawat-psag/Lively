from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.child_habit_fridge_inventory import ChildHabitFridgeInventory
from app.models.habit import Habit
from app.models.simulation import Simulation
from app.models.user import User
from app.repositories.habit_tracker_repository import HabitTrackerRepository
from app.schemas.habit_tracker import (
    CompleteHabitData,
    CompleteHabitRequest,
    CompleteHabitResponse,
    FridgeInventoryQuantities,
    HabitCompletionInfo,
    HabitRewardInfo,
    HabitTrackerActivityPublic,
    HabitTrackerChildHabitPublic,
    HabitTrackerChildPublic,
    HabitTrackerDetailsData,
    HabitTrackerDetailsResponse,
    HabitTrackerHabitCatalogItemPublic,
    HabitTrackerPayloadPublic,
    HabitTrackerStepPublic,
)

INVENTORY_LIMIT = 9
REWARD_ATTEMPTED = 9


class HabitTrackerService:
    def __init__(self, db: Session) -> None:
        self.repo = HabitTrackerRepository(db)

    def get_details(self, child: User) -> HabitTrackerDetailsResponse:
        habits = self.repo.list_active_habits()
        habit_ids = [habit.id for habit in habits]
        preferences = self.repo.list_child_preferences(child_user_id=child.id, habit_ids=habit_ids)
        completed_map = self.repo.list_completed_dates_by_habit(
            child_user_id=child.id,
            habit_ids=habit_ids,
        )
        activity_by_id = {
            habit.simulation.id: habit.simulation
            for habit in habits
            if habit.simulation is not None
        }

        habit_catalog: dict[str, HabitTrackerHabitCatalogItemPublic] = {}
        child_habits: list[HabitTrackerChildHabitPublic] = []

        for habit in habits:
            simulation = habit.simulation
            if simulation is None or not habit.habit_key or not simulation.activity_key:
                continue

            pref = preferences.get(habit.id)
            if pref and pref.default_activity_id in activity_by_id:
                selected = activity_by_id[pref.default_activity_id]
            else:
                selected = simulation

            selected_key = selected.activity_key or simulation.activity_key
            steps = sorted(habit.steps, key=lambda s: (s.display_order, s.id))
            activity_steps = [
                HabitTrackerStepPublic(
                    stepId=step.step_key,
                    order=step.display_order,
                    image=step.image_key,
                    text=step.question,
                    buttonText=step.button_text
                    or ("Finish" if idx == len(steps) - 1 else "Next"),
                )
                for idx, step in enumerate(steps)
            ]

            habit_catalog[habit.habit_key] = HabitTrackerHabitCatalogItemPublic(
                habitId=habit.habit_key,
                title=habit.header_text,
                isActive=True,
                cardColor=habit.card_color,
                defaultActivityId=selected_key,
                activities={
                    simulation.activity_key: HabitTrackerActivityPublic(
                        activityId=simulation.activity_key,
                        title=simulation.simulation_name,
                        isActive=True,
                        steps=activity_steps,
                    )
                },
            )
            child_habits.append(
                HabitTrackerChildHabitPublic(
                    habitId=habit.habit_key,
                    completedDates=completed_map.get(habit.id, []),
                )
            )

        return HabitTrackerDetailsResponse(
            success=True,
            message="Habit tracker fetched successfully",
            data=HabitTrackerDetailsData(
                habitTracker=HabitTrackerPayloadPublic(
                    habitCatalog=habit_catalog,
                    child=HabitTrackerChildPublic(
                        childId=str(child.id),
                        habits=child_habits,
                    ),
                )
            ),
        )

    def complete_habit(self, child: User, payload: CompleteHabitRequest) -> CompleteHabitResponse:
        today = datetime.now(timezone.utc).date()
        if payload.date > today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Future completion date is not allowed"},
            )

        habit = self.repo.get_habit_by_key(payload.habit_id)
        if habit is None or habit.simulation is None or not habit.habit_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "message": "Habit not found"},
            )

        activity = self.repo.get_activity_by_key(payload.default_activity_id)
        if activity is None or activity.id != habit.simulation_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Activity does not belong to habit"},
            )

        existing = self.repo.get_completion(
            child_user_id=child.id,
            habit_id=habit.id,
            tracking_date=payload.date,
        )
        fridge = self.repo.get_or_create_fridge(child_user_id=child.id, habit_id=habit.id)

        if existing is not None:
            return self._build_complete_response(
                child=child,
                habit=habit,
                completed_date=payload.date,
                streak_continued=False,
                streak_reset=False,
                reward_icon=self._reward_icon_for_streak(fridge.current_streak or 1),
                attempted_quantity=0,
                added_quantity=0,
                inventory_limit_reached=True,
                fridge=fridge,
                message="Habit already completed for this date",
            )

        streak_continued, streak_reset, new_streak, clear_inventory = self._compute_streak(
            fridge.last_completed_date,
            fridge.current_streak,
            payload.date,
        )
        reward_icon = self._reward_icon_for_streak(new_streak)
        current_qty = getattr(fridge, reward_icon) if not clear_inventory else 0
        available_space = INVENTORY_LIMIT - current_qty
        added_quantity = min(REWARD_ATTEMPTED, available_space)
        inventory_limit_reached = added_quantity < REWARD_ATTEMPTED

        fridge = self.repo.complete_habit_transaction(
            child_user_id=child.id,
            habit=habit,
            activity=activity,
            tracking_date=payload.date,
            fridge=fridge,
            streak_continued=streak_continued,
            streak_reset=streak_reset,
            new_streak=new_streak,
            reward_icon=reward_icon,
            added_quantity=added_quantity,
            clear_inventory=clear_inventory,
        )

        return self._build_complete_response(
            child=child,
            habit=habit,
            completed_date=payload.date,
            streak_continued=streak_continued,
            streak_reset=streak_reset,
            reward_icon=reward_icon,
            attempted_quantity=REWARD_ATTEMPTED,
            added_quantity=added_quantity,
            inventory_limit_reached=inventory_limit_reached,
            fridge=fridge,
            message="Habit completion saved successfully",
        )

    @staticmethod
    def _reward_icon_for_streak(streak: int) -> str:
        if streak >= 8:
            return "sardini"
        if streak >= 3:
            return "mussels"
        return "fries"

    @staticmethod
    def _compute_streak(
        last_completed: date | None,
        current_streak: int,
        completed_date: date,
    ) -> tuple[bool, bool, int, bool]:
        if last_completed is None:
            return False, False, 1, False
        if completed_date == last_completed + timedelta(days=1):
            return True, False, current_streak + 1, False
        if completed_date == last_completed:
            return False, False, max(current_streak, 1), False
        return False, True, 1, True

    def _build_complete_response(
        self,
        *,
        child: User,
        habit: Habit,
        completed_date: date,
        streak_continued: bool,
        streak_reset: bool,
        reward_icon: str,
        attempted_quantity: int,
        added_quantity: int,
        inventory_limit_reached: bool,
        fridge: ChildHabitFridgeInventory,
        message: str,
    ) -> CompleteHabitResponse:
        return CompleteHabitResponse(
            success=True,
            message=message,
            data=CompleteHabitData(
                childId=str(child.id),
                habitId=habit.habit_key or str(habit.id),
                completion=HabitCompletionInfo(
                    completedDate=completed_date,
                    streakContinued=streak_continued,
                    streakReset=streak_reset,
                ),
                reward=HabitRewardInfo(
                    icon=reward_icon,
                    attemptedQuantity=attempted_quantity,
                    addedQuantity=added_quantity,
                    inventoryLimitReached=inventory_limit_reached,
                ),
                inventory=FridgeInventoryQuantities(
                    fries=fridge.fries,
                    mussels=fridge.mussels,
                    sardini=fridge.sardini,
                ),
                updatedAt=fridge.updated_at or datetime.now(timezone.utc),
            ),
        )
