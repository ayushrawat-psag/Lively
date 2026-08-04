from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.child_habit_preference import ChildHabitPreference
from app.models.enums import ContentStatus, HabitTrackerStatus, SimulationType
from app.models.habit import Habit
from app.models.habit_step import HabitStep
from app.models.habit_tracker import HabitTracker
from app.models.simulation import Simulation


class HabitTrackerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_active_habits(self) -> list[Habit]:
        stmt = (
            select(Habit)
            .options(
                selectinload(Habit.steps).selectinload(HabitStep.options),
                selectinload(Habit.simulation),
            )
            .join(Simulation, Habit.simulation_id == Simulation.id)
            .where(
                Habit.status == ContentStatus.ACTIVE,
                Simulation.status == ContentStatus.ACTIVE,
                Simulation.simulation_type == SimulationType.HABIT,
            )
            .order_by(Habit.created_at.asc(), Habit.id.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_habit_with_simulation(self, habit_id: UUID) -> Habit | None:
        stmt = (
            select(Habit)
            .options(selectinload(Habit.simulation))
            .join(Simulation, Habit.simulation_id == Simulation.id)
            .where(
                Habit.id == habit_id,
                Habit.status == ContentStatus.ACTIVE,
                Simulation.status == ContentStatus.ACTIVE,
                Simulation.simulation_type == SimulationType.HABIT,
            )
        )
        return self.db.scalars(stmt).first()

    def list_child_preferences(
        self,
        *,
        child_user_id: UUID,
        habit_ids: list[UUID],
    ) -> dict[UUID, ChildHabitPreference]:
        if not habit_ids:
            return {}
        stmt = select(ChildHabitPreference).where(
            ChildHabitPreference.child_user_id == child_user_id,
            ChildHabitPreference.habit_id.in_(habit_ids),
        )
        return {row.habit_id: row for row in self.db.scalars(stmt).all()}

    def upsert_child_preference(
        self,
        *,
        child_user_id: UUID,
        habit_id: UUID,
        default_activity_id: UUID,
    ) -> ChildHabitPreference:
        stmt = select(ChildHabitPreference).where(
            ChildHabitPreference.child_user_id == child_user_id,
            ChildHabitPreference.habit_id == habit_id,
        )
        preference = self.db.scalars(stmt).first()
        if preference is None:
            preference = ChildHabitPreference(
                child_user_id=child_user_id,
                habit_id=habit_id,
                default_activity_id=default_activity_id,
            )
            self.db.add(preference)
        else:
            preference.default_activity_id = default_activity_id
        self.db.commit()
        self.db.refresh(preference)
        return preference

    def upsert_completion(
        self,
        *,
        child_user_id: UUID,
        habit_id: UUID,
        tracking_date,
    ) -> HabitTracker:
        stmt = select(HabitTracker).where(
            HabitTracker.user_id == child_user_id,
            HabitTracker.habit_id == habit_id,
            HabitTracker.tracking_date == tracking_date,
        )
        row = self.db.scalars(stmt).first()
        now = datetime.now(timezone.utc)
        if row is None:
            row = HabitTracker(
                user_id=child_user_id,
                habit_id=habit_id,
                tracking_date=tracking_date,
                status=HabitTrackerStatus.COMPLETED,
                completed_at=now,
            )
            self.db.add(row)
        else:
            row.status = HabitTrackerStatus.COMPLETED
            row.completed_at = row.completed_at or now
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_completed_dates_by_habit(
        self,
        *,
        child_user_id: UUID,
        habit_ids: list[UUID],
    ) -> dict[UUID, list]:
        if not habit_ids:
            return {}
        stmt = (
            select(HabitTracker.habit_id, HabitTracker.tracking_date)
            .where(
                HabitTracker.user_id == child_user_id,
                HabitTracker.habit_id.in_(habit_ids),
                HabitTracker.status == HabitTrackerStatus.COMPLETED,
            )
            .order_by(HabitTracker.tracking_date.asc())
        )
        output: dict[UUID, list] = {habit_id: [] for habit_id in habit_ids}
        for habit_id, tracking_date in self.db.execute(stmt):
            output.setdefault(habit_id, []).append(tracking_date)
        return output
