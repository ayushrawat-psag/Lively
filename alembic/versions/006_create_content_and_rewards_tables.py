"""create content and rewards tables

Revision ID: 006_create_content_and_rewards_tables
Revises: 005_create_core_org_tables
Create Date: 2026-07-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_content_rewards"
down_revision: Union[str, None] = "005_core_org"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

content_status = postgresql.ENUM("ACTIVE", "INACTIVE", name="content_status", create_type=False)
simulation_type = postgresql.ENUM("SCRIPT", "HABIT", "GAME", name="simulation_type", create_type=False)
habit_type = postgresql.ENUM("SETUP", "DAILY", name="habit_type", create_type=False)
habit_tracker_status = postgresql.ENUM(
    "COMPLETED", "INCOMPLETE", name="habit_tracker_status", create_type=False
)
reward_type = postgresql.ENUM("FOOD", "MUSEUM", "CHIP", name="reward_type", create_type=False)
user_reward_entry_type = postgresql.ENUM(
    "STARS_EARNED",
    "REWARD_CLAIMED",
    "PRIZE_ITEM_UNLOCKED",
    name="user_reward_entry_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM("ACTIVE", "INACTIVE", name="content_status").create(bind, checkfirst=True)
    postgresql.ENUM("SCRIPT", "HABIT", "GAME", name="simulation_type").create(bind, checkfirst=True)
    postgresql.ENUM("SETUP", "DAILY", name="habit_type").create(bind, checkfirst=True)
    postgresql.ENUM("COMPLETED", "INCOMPLETE", name="habit_tracker_status").create(bind, checkfirst=True)
    postgresql.ENUM("FOOD", "MUSEUM", "CHIP", name="reward_type").create(bind, checkfirst=True)
    postgresql.ENUM(
        "STARS_EARNED",
        "REWARD_CLAIMED",
        "PRIZE_ITEM_UNLOCKED",
        name="user_reward_entry_type",
    ).create(bind, checkfirst=True)

    op.create_table(
        "islands",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("island_name", sa.String(length=150), nullable=False),
        sa.Column("badge_icon_url", sa.Text(), nullable=True),
        sa.Column("status", content_status, nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("island_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_name", sa.String(length=150), nullable=False),
        sa.Column("status", content_status, nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["island_id"], ["islands.id"]),
    )
    op.create_index("ix_locations_island_id", "locations", ["island_id"])

    op.create_table(
        "simulations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("island_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("simulation_name", sa.String(length=200), nullable=False),
        sa.Column("hero_image_url", sa.Text(), nullable=True),
        sa.Column("simulation_type", simulation_type, nullable=False),
        sa.Column("status", content_status, nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["island_id"], ["islands.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
    )
    op.create_index("ix_simulations_island_id", "simulations", ["island_id"])
    op.create_index("ix_simulations_location_id", "simulations", ["location_id"])

    op.create_table(
        "simulation_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("simulation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("option_number", sa.Integer(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"]),
        sa.UniqueConstraint(
            "simulation_id",
            "option_number",
            name="uq_simulation_answers_simulation_option",
        ),
    )
    op.create_index("ix_simulation_answers_simulation_id", "simulation_answers", ["simulation_id"])

    op.create_table(
        "prize_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("simulation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("header_text", sa.String(length=200), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("sprite_image_url", sa.Text(), nullable=False),
        sa.Column("status", content_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"]),
    )
    op.create_index("ix_prize_items_simulation_id", "prize_items", ["simulation_id"])

    op.create_table(
        "habits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("simulation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("header_text", sa.String(length=200), nullable=False),
        sa.Column("header_icon_url", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("stars_to_earn", sa.Integer(), nullable=False),
        sa.Column("habit_type", habit_type, nullable=False),
        sa.Column("status", content_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"]),
        sa.CheckConstraint("stars_to_earn >= 0", name="ck_habits_stars_to_earn_nonneg"),
    )
    op.create_index("ix_habits_simulation_id", "habits", ["simulation_id"])

    op.create_table(
        "habit_tracker",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("habit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tracking_date", sa.Date(), nullable=False),
        sa.Column("status", habit_tracker_status, nullable=False),
        sa.Column("evidence_image_url", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["habit_id"], ["habits.id"]),
        sa.UniqueConstraint(
            "user_id",
            "habit_id",
            "tracking_date",
            name="uq_habit_tracker_user_habit_date",
        ),
    )
    op.create_index("ix_habit_tracker_user_id", "habit_tracker", ["user_id"])
    op.create_index("ix_habit_tracker_habit_id", "habit_tracker", ["habit_id"])
    op.create_index("ix_habit_tracker_user_tracking_date", "habit_tracker", ["user_id", "tracking_date"])

    op.create_table(
        "rewards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("reward_name", sa.String(length=200), nullable=False),
        sa.Column("reward_type", reward_type, nullable=False),
        sa.Column("stars_required", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("stars_required > 0", name="ck_rewards_stars_required_positive"),
    )

    op.create_table(
        "user_rewards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_type", user_reward_entry_type, nullable=False),
        sa.Column("habit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reward_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prize_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("stars_delta", sa.Integer(), server_default="0", nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["habit_id"], ["habits.id"]),
        sa.ForeignKeyConstraint(["reward_id"], ["rewards.id"]),
        sa.ForeignKeyConstraint(["prize_item_id"], ["prize_items.id"]),
    )
    op.create_index("ix_user_rewards_user_id", "user_rewards", ["user_id"])
    op.create_index("ix_user_rewards_habit_id", "user_rewards", ["habit_id"])
    op.create_index("ix_user_rewards_reward_id", "user_rewards", ["reward_id"])
    op.create_index("ix_user_rewards_prize_item_id", "user_rewards", ["prize_item_id"])
    op.create_index("ix_user_rewards_user_occurred_at", "user_rewards", ["user_id", "occurred_at"])
    op.create_index(
        "uq_user_rewards_user_prize_item",
        "user_rewards",
        ["user_id", "prize_item_id"],
        unique=True,
        postgresql_where=sa.text("prize_item_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_user_rewards_user_prize_item", table_name="user_rewards")
    op.drop_index("ix_user_rewards_user_occurred_at", table_name="user_rewards")
    op.drop_index("ix_user_rewards_prize_item_id", table_name="user_rewards")
    op.drop_index("ix_user_rewards_reward_id", table_name="user_rewards")
    op.drop_index("ix_user_rewards_habit_id", table_name="user_rewards")
    op.drop_index("ix_user_rewards_user_id", table_name="user_rewards")
    op.drop_table("user_rewards")
    op.drop_table("rewards")
    op.drop_index("ix_habit_tracker_user_tracking_date", table_name="habit_tracker")
    op.drop_index("ix_habit_tracker_habit_id", table_name="habit_tracker")
    op.drop_index("ix_habit_tracker_user_id", table_name="habit_tracker")
    op.drop_table("habit_tracker")
    op.drop_index("ix_habits_simulation_id", table_name="habits")
    op.drop_table("habits")
    op.drop_index("ix_prize_items_simulation_id", table_name="prize_items")
    op.drop_table("prize_items")
    op.drop_index("ix_simulation_answers_simulation_id", table_name="simulation_answers")
    op.drop_table("simulation_answers")
    op.drop_index("ix_simulations_location_id", table_name="simulations")
    op.drop_index("ix_simulations_island_id", table_name="simulations")
    op.drop_table("simulations")
    op.drop_index("ix_locations_island_id", table_name="locations")
    op.drop_table("locations")
    op.drop_table("islands")

    bind = op.get_bind()
    postgresql.ENUM(name="user_reward_entry_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="reward_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="habit_tracker_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="habit_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="simulation_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="content_status").drop(bind, checkfirst=True)
