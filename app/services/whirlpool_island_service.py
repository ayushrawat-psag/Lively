from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import SimulationType
from app.models.simulation import Simulation
from app.models.user import User
from app.repositories.whirlpool_island_repository import (
    WHIRLPOOL_ACTIVITY_KEYS,
    WhirlpoolIslandRepository,
)
from app.schemas.whirlpool_island import (
    ActivityProgressPublic,
    ActivityPublic,
    CompleteActivityData,
    CompleteActivityRequest,
    CompleteActivityResponse,
    CompleteIslandData,
    CompleteIslandRequest,
    CompleteIslandResponse,
    HabitCorrectResultPublic,
    HabitPublic,
    HabitStepOptionPublic,
    HabitStepPublic,
    IslandStatusPublic,
    ResultPublic,
    ScriptAnswerPublic,
    ScriptPublic,
    WhirlpoolIslandData,
    WhirlpoolIslandDetailsResponse,
)


class WhirlpoolIslandService:
    def __init__(self, db: Session) -> None:
        self.repo = WhirlpoolIslandRepository(db)

    def get_details(self, child: User) -> WhirlpoolIslandDetailsResponse:
        island = self.repo.get_whirlpool_island()
        if island is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "message": "Whirlpool Island not found"},
            )

        simulations = self.repo.list_whirlpool_activities(island.id)
        progress_map = self.repo.list_simulation_progress(
            child_user_id=child.id,
            simulation_ids=[sim.id for sim in simulations],
        )
        island_progress = self.repo.get_island_progress(
            child_user_id=child.id,
            island_id=island.id,
        )

        activities = [
            self._to_activity_public(sim, progress_map.get(sim.id))
            for sim in simulations
            if sim.activity_key
        ]

        return WhirlpoolIslandDetailsResponse(
            success=True,
            message="Whirlpool Island details fetched successfully",
            data=WhirlpoolIslandData(
                island=IslandStatusPublic(
                    completed=bool(island_progress and island_progress.completed),
                    completedAt=island_progress.completed_at if island_progress else None,
                ),
                activities=activities,
            ),
        )

    def complete_activity(
        self,
        child: User,
        activity_id: str,
        payload: CompleteActivityRequest,
    ) -> CompleteActivityResponse:
        if activity_id not in WHIRLPOOL_ACTIVITY_KEYS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "message": "Activity not found"},
            )

        island = self.repo.get_whirlpool_island()
        if island is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "message": "Whirlpool Island not found"},
            )

        simulation = self.repo.get_activity_by_key(island.id, activity_id)
        if simulation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "message": "Activity not found"},
            )

        existing = self.repo.get_simulation_progress(
            child_user_id=child.id,
            simulation_id=simulation.id,
        )
        attempts = payload.attempts if payload.attempts is not None else (
            (existing.attempts + 1) if existing else 1
        )

        progress = self.repo.upsert_simulation_progress(
            child_user_id=child.id,
            simulation_id=simulation.id,
            completed=payload.completed,
            attempts=attempts,
        )

        return CompleteActivityResponse(
            success=True,
            message="Activity completed successfully",
            data=CompleteActivityData(
                activityId=activity_id,
                childId=str(child.id),
                activityType=self._public_type(simulation.simulation_type),
                isCorrect=payload.completed,
                progress=ActivityProgressPublic(
                    completed=progress.completed,
                    attempts=progress.attempts,
                    completedAt=progress.completed_at,
                ),
            ),
        )

    def complete_island(
        self,
        child: User,
        payload: CompleteIslandRequest,
    ) -> CompleteIslandResponse:
        island = self.repo.get_whirlpool_island()
        if island is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "message": "Whirlpool Island not found"},
            )

        progress = self.repo.upsert_island_progress(
            child_user_id=child.id,
            island_id=island.id,
            completed=payload.completed,
        )

        return CompleteIslandResponse(
            success=True,
            message="Whirlpool Island completed successfully",
            data=CompleteIslandData(
                childId=str(child.id),
                island=IslandStatusPublic(
                    completed=progress.completed,
                    completedAt=progress.completed_at,
                ),
            ),
        )

    @staticmethod
    def _public_type(simulation_type: SimulationType) -> str:
        return simulation_type.value.lower()

    def _to_activity_public(
        self,
        simulation: Simulation,
        progress,
    ) -> ActivityPublic:
        activity_type = self._public_type(simulation.simulation_type)
        progress_public = ActivityProgressPublic(
            completed=bool(progress and progress.completed),
            attempts=progress.attempts if progress else 0,
            completedAt=progress.completed_at if progress else None,
        )

        script = None
        habit = None
        if simulation.simulation_type == SimulationType.SCRIPT:
            script = ScriptPublic(
                question=simulation.question_text or "",
                answers=[
                    ScriptAnswerPublic(
                        id=answer.answer_key or str(answer.id),
                        label=answer.answer,
                        isCorrect=answer.is_correct,
                    )
                    for answer in sorted(
                        simulation.answers,
                        key=lambda a: (a.option_number, a.id),
                    )
                ],
                correctResult=ResultPublic(
                    title=simulation.correct_result_title or "",
                    message=simulation.correct_result_message or "",
                ),
                wrongResult=ResultPublic(
                    title=simulation.wrong_result_title or "",
                    message=simulation.wrong_result_message or "",
                ),
            )
        elif simulation.simulation_type == SimulationType.HABIT:
            habit_row = simulation.habits[0] if simulation.habits else None
            if habit_row is not None:
                habit = HabitPublic(
                    description=habit_row.body_text or habit_row.header_text,
                    steps=[
                        HabitStepPublic(
                            id=step.step_key,
                            type=step.step_type,
                            question=step.question,
                            options=[
                                HabitStepOptionPublic(
                                    id=option.option_key,
                                    label=option.label,
                                )
                                for option in sorted(
                                    step.options,
                                    key=lambda o: (o.display_order, o.id),
                                )
                            ],
                        )
                        for step in sorted(
                            habit_row.steps,
                            key=lambda s: (s.display_order, s.id),
                        )
                    ],
                    correctResult=HabitCorrectResultPublic(
                        title=habit_row.correct_result_title or "",
                    ),
                )

        return ActivityPublic(
            id=simulation.activity_key or "",
            type=activity_type,
            status="available",
            title=simulation.simulation_name,
            progress=progress_public,
            script=script,
            habit=habit,
        )
