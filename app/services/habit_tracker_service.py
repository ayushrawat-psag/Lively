from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.habit_tracker_repository import HabitTrackerRepository
from app.schemas.habit_tracker import (
    CompleteHabitData,
    CompleteHabitRequest,
    CompleteHabitResponse,
    HabitTrackerActivityPublic,
    HabitTrackerChildHabitPublic,
    HabitTrackerChildPublic,
    HabitTrackerDetailsData,
    HabitTrackerDetailsResponse,
    HabitTrackerHabitCatalogItemPublic,
    HabitTrackerPayloadPublic,
    HabitTrackerStepPublic,
)


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

        habit_catalog: dict[str, HabitTrackerHabitCatalogItemPublic] = {}
        child_habits: list[HabitTrackerChildHabitPublic] = []

        for habit in habits:
            simulation = habit.simulation
            if simulation is None:
                continue

            pref = preferences.get(habit.id)
            selected_activity_id = pref.default_activity_id if pref else simulation.id
            habit_id_str = str(habit.id)
            activity_id_str = str(simulation.id)

            steps = sorted(habit.steps, key=lambda s: (s.display_order, s.id))
            activity_steps = [
                HabitTrackerStepPublic(
                    stepId=step.step_key,
                    order=step.display_order,
                    image=None,
                    text=step.question,
                    buttonText="Finish" if idx == len(steps) - 1 else "Next",
                )
                for idx, step in enumerate(steps)
            ]

            habit_catalog[habit_id_str] = HabitTrackerHabitCatalogItemPublic(
                habitId=habit_id_str,
                title=habit.header_text,
                isActive=True,
                cardColor=None,
                defaultActivityId=str(selected_activity_id),
                activities={
                    activity_id_str: HabitTrackerActivityPublic(
                        activityId=activity_id_str,
                        title=simulation.simulation_name,
                        isActive=True,
                        steps=activity_steps,
                    )
                },
            )

            child_habits.append(
                HabitTrackerChildHabitPublic(
                    habitId=habit_id_str,
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
        habit_id = self._parse_uuid(payload.habit_id, "Invalid habitId")
        default_activity_id = self._parse_uuid(payload.default_activity_id, "Invalid defaultActivityId")

        habit = self.repo.get_habit_with_simulation(habit_id)
        if habit is None or habit.simulation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "message": "Habit not found"},
            )

        if habit.simulation.id != default_activity_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Activity does not belong to habit"},
            )

        self.repo.upsert_child_preference(
            child_user_id=child.id,
            habit_id=habit.id,
            default_activity_id=default_activity_id,
        )
        self.repo.upsert_completion(
            child_user_id=child.id,
            habit_id=habit.id,
            tracking_date=payload.date,
        )
        completed_map = self.repo.list_completed_dates_by_habit(
            child_user_id=child.id,
            habit_ids=[habit.id],
        )

        return CompleteHabitResponse(
            success=True,
            message="Habit completion saved successfully",
            data=CompleteHabitData(
                habitId=str(habit.id),
                defaultActivityId=str(default_activity_id),
                completedDates=completed_map.get(habit.id, []),
            ),
        )

    @staticmethod
    def _parse_uuid(value: str, message: str) -> UUID:
        try:
            return UUID(value)
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": message},
            ) from exc
