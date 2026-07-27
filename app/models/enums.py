from __future__ import annotations

import enum


class UserType(str, enum.Enum):
    PARENT = "PARENT"
    CHILD = "CHILD"
    TEACHER = "TEACHER"
    GUARDIAN = "GUARDIAN"


class AgeCohort(str, enum.Enum):
    TODDLER = "TODDLER"
    CHILD = "CHILD"
    TWEEN = "TWEEN"
    TEEN = "TEEN"
    ADULT = "ADULT"


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class ContentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class SimulationType(str, enum.Enum):
    SCRIPT = "SCRIPT"
    HABIT = "HABIT"
    GAME = "GAME"


class HabitType(str, enum.Enum):
    SETUP = "SETUP"
    DAILY = "DAILY"


class HabitTrackerStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"
    INCOMPLETE = "INCOMPLETE"


class RewardType(str, enum.Enum):
    FOOD = "FOOD"
    MUSEUM = "MUSEUM"
    CHIP = "CHIP"


class UserRewardEntryType(str, enum.Enum):
    STARS_EARNED = "STARS_EARNED"
    REWARD_CLAIMED = "REWARD_CLAIMED"
    PRIZE_ITEM_UNLOCKED = "PRIZE_ITEM_UNLOCKED"


class BillingInterval(str, enum.Enum):
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"
    ONE_TIME = "ONE_TIME"


class DiscountType(str, enum.Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED_AMOUNT = "FIXED_AMOUNT"


class LearnerPermitStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
