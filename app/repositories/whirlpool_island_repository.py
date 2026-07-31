from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.child_island_progress import ChildIslandProgress
from app.models.child_simulation_progress import ChildSimulationProgress
from app.models.enums import ContentStatus
from app.models.habit import Habit
from app.models.habit_step import HabitStep
from app.models.island import Island
from app.models.simulation import Simulation


WHIRLPOOL_COMIC_NUMBER = 0

WHIRLPOOL_ACTIVITY_KEYS = frozenset(
    {
        "one_more_sign",
        "stop_star_fish",
        "relaxing_chair",
        "beach_towel",
        "sleeping_jellyfish",
        "flip_flops",
        "palm_tree_hammock",
        "backpack_turtle",
        "water_gun_octopus",
        "dj_sloth_booth",
        "algorithm_crown",
        "hermit_crab",
        "binoculars",
        "beach_ball",
        "pelican_on_treadmill",
        "crab_s_house",
        "coffee_stand_brb",
        "coconut_with_headphones",
        "souvenir_stand",
    }
)


class WhirlpoolIslandRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_whirlpool_island(self) -> Island | None:
        stmt = select(Island).where(
            Island.comic_number == WHIRLPOOL_COMIC_NUMBER,
            Island.status == ContentStatus.ACTIVE,
        )
        return self.db.scalars(stmt).first()

    def list_whirlpool_activities(self, island_id: UUID) -> list[Simulation]:
        stmt = (
            select(Simulation)
            .options(
                selectinload(Simulation.answers),
                selectinload(Simulation.habits).selectinload(Habit.steps).selectinload(
                    HabitStep.options
                ),
            )
            .where(
                Simulation.island_id == island_id,
                Simulation.status == ContentStatus.ACTIVE,
                Simulation.activity_key.is_not(None),
            )
            .order_by(Simulation.display_order.asc(), Simulation.id.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_activity_by_key(self, island_id: UUID, activity_key: str) -> Simulation | None:
        stmt = (
            select(Simulation)
            .where(
                Simulation.island_id == island_id,
                Simulation.activity_key == activity_key,
                Simulation.status == ContentStatus.ACTIVE,
            )
        )
        return self.db.scalars(stmt).first()

    def get_island_progress(
        self, *, child_user_id: UUID, island_id: UUID
    ) -> ChildIslandProgress | None:
        stmt = select(ChildIslandProgress).where(
            ChildIslandProgress.child_user_id == child_user_id,
            ChildIslandProgress.island_id == island_id,
        )
        return self.db.scalars(stmt).first()

    def list_simulation_progress(
        self, *, child_user_id: UUID, simulation_ids: list[UUID]
    ) -> dict[UUID, ChildSimulationProgress]:
        if not simulation_ids:
            return {}
        stmt = select(ChildSimulationProgress).where(
            ChildSimulationProgress.child_user_id == child_user_id,
            ChildSimulationProgress.simulation_id.in_(simulation_ids),
        )
        return {row.simulation_id: row for row in self.db.scalars(stmt).all()}

    def get_simulation_progress(
        self, *, child_user_id: UUID, simulation_id: UUID
    ) -> ChildSimulationProgress | None:
        stmt = select(ChildSimulationProgress).where(
            ChildSimulationProgress.child_user_id == child_user_id,
            ChildSimulationProgress.simulation_id == simulation_id,
        )
        return self.db.scalars(stmt).first()

    def upsert_simulation_progress(
        self,
        *,
        child_user_id: UUID,
        simulation_id: UUID,
        completed: bool,
        attempts: int,
    ) -> ChildSimulationProgress:
        progress = self.get_simulation_progress(
            child_user_id=child_user_id,
            simulation_id=simulation_id,
        )
        now = datetime.now(timezone.utc)
        if progress is None:
            progress = ChildSimulationProgress(
                child_user_id=child_user_id,
                simulation_id=simulation_id,
                completed=completed,
                attempts=attempts,
                completed_at=now if completed else None,
            )
            self.db.add(progress)
        else:
            progress.attempts = attempts
            progress.completed = completed
            if completed:
                progress.completed_at = progress.completed_at or now
            else:
                progress.completed_at = None
        self.db.commit()
        self.db.refresh(progress)
        return progress

    def upsert_island_progress(
        self,
        *,
        child_user_id: UUID,
        island_id: UUID,
        completed: bool,
    ) -> ChildIslandProgress:
        progress = self.get_island_progress(child_user_id=child_user_id, island_id=island_id)
        now = datetime.now(timezone.utc)
        if progress is None:
            progress = ChildIslandProgress(
                child_user_id=child_user_id,
                island_id=island_id,
                completed=completed,
                completed_at=now if completed else None,
            )
            self.db.add(progress)
        else:
            progress.completed = completed
            if completed:
                progress.completed_at = progress.completed_at or now
            else:
                progress.completed_at = None
        self.db.commit()
        self.db.refresh(progress)
        return progress
