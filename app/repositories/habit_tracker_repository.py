from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.child_habit_fridge_inventory import ChildHabitFridgeInventory
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
                Habit.habit_key.is_not(None),
                Simulation.status == ContentStatus.ACTIVE,
                Simulation.simulation_type == SimulationType.HABIT,
            )
            .order_by(Habit.created_at.asc(), Habit.id.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_habit_by_key(self, habit_key: str) -> Habit | None:
        stmt = (
            select(Habit)
            .options(
                selectinload(Habit.steps),
                selectinload(Habit.simulation),
            )
            .join(Simulation, Habit.simulation_id == Simulation.id)
            .where(
                Habit.habit_key == habit_key,
                Habit.status == ContentStatus.ACTIVE,
                Simulation.status == ContentStatus.ACTIVE,
                Simulation.simulation_type == SimulationType.HABIT,
            )
        )
        return self.db.scalars(stmt).first()

    def get_activity_by_key(self, activity_key: str) -> Simulation | None:
        stmt = select(Simulation).where(
            Simulation.activity_key == activity_key,
            Simulation.status == ContentStatus.ACTIVE,
            Simulation.simulation_type == SimulationType.HABIT,
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

    def get_completion(
        self,
        *,
        child_user_id: UUID,
        habit_id: UUID,
        tracking_date: date,
    ) -> HabitTracker | None:
        stmt = select(HabitTracker).where(
            HabitTracker.user_id == child_user_id,
            HabitTracker.habit_id == habit_id,
            HabitTracker.tracking_date == tracking_date,
            HabitTracker.status == HabitTrackerStatus.COMPLETED,
        )
        return self.db.scalars(stmt).first()

    def get_or_create_fridge(
        self,
        *,
        child_user_id: UUID,
        habit_id: UUID,
    ) -> ChildHabitFridgeInventory:
        stmt = select(ChildHabitFridgeInventory).where(
            ChildHabitFridgeInventory.child_user_id == child_user_id,
            ChildHabitFridgeInventory.habit_id == habit_id,
        )
        row = self.db.scalars(stmt).first()
        if row is None:
            row = ChildHabitFridgeInventory(
                child_user_id=child_user_id,
                habit_id=habit_id,
                fries=0,
                mussels=0,
                sardini=0,
                current_streak=0,
            )
            self.db.add(row)
            self.db.flush()
        return row

    def list_fridge_rows(
        self,
        *,
        child_user_id: UUID,
        habit_ids: list[UUID] | None = None,
    ) -> list[ChildHabitFridgeInventory]:
        stmt = select(ChildHabitFridgeInventory).where(
            ChildHabitFridgeInventory.child_user_id == child_user_id,
        )
        if habit_ids is not None:
            if not habit_ids:
                return []
            stmt = stmt.where(ChildHabitFridgeInventory.habit_id.in_(habit_ids))
        return list(self.db.scalars(stmt).all())

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

    def complete_habit_transaction(
        self,
        *,
        child_user_id: UUID,
        habit: Habit,
        activity: Simulation,
        tracking_date: date,
        fridge: ChildHabitFridgeInventory,
        streak_continued: bool,
        streak_reset: bool,
        new_streak: int,
        reward_icon: str,
        added_quantity: int,
        clear_inventory: bool,
    ) -> ChildHabitFridgeInventory:
        now = datetime.now(timezone.utc)

        pref_stmt = select(ChildHabitPreference).where(
            ChildHabitPreference.child_user_id == child_user_id,
            ChildHabitPreference.habit_id == habit.id,
        )
        preference = self.db.scalars(pref_stmt).first()
        if preference is None:
            preference = ChildHabitPreference(
                child_user_id=child_user_id,
                habit_id=habit.id,
                default_activity_id=activity.id,
            )
            self.db.add(preference)
        else:
            preference.default_activity_id = activity.id

        tracker = HabitTracker(
            user_id=child_user_id,
            habit_id=habit.id,
            tracking_date=tracking_date,
            status=HabitTrackerStatus.COMPLETED,
            completed_at=now,
        )
        self.db.add(tracker)

        if clear_inventory:
            fridge.fries = 0
            fridge.mussels = 0
            fridge.sardini = 0

        fridge.current_streak = new_streak
        fridge.last_completed_date = tracking_date
        current = getattr(fridge, reward_icon)
        setattr(fridge, reward_icon, current + added_quantity)

        self.db.commit()
        self.db.refresh(fridge)
        return fridge
