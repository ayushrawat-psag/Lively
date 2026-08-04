"""add fridge inventory and habit tracker catalog keys

Revision ID: 018_habit_fridge_inventory
Revises: 017_add_child_habit_preferences
Create Date: 2026-08-04
"""

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "018_habit_fridge_inventory"
down_revision: Union[str, None] = "017_add_child_habit_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


HABIT_CATALOG = [
    {
        "habit_key": "body_checkin",
        "title": "Body Check-in",
        "card_color": "#89C27D",
        "activity_key": "heart_beat",
        "activity_title": "Heart beat",
        "steps": [
            {
                "step_key": "hand_on_chest",
                "order": 1,
                "image_key": "chip_hand_on_chest.png",
                "text": "Put a hand on your chest. Can you feel your heart beating?",
                "button_text": "Next",
            },
            {
                "step_key": "count_heartbeats",
                "order": 2,
                "image_key": "chip_counting.png",
                "text": "Count 5 heart beats.",
                "button_text": "Next",
            },
            {
                "step_key": "how_did_it_feel",
                "order": 3,
                "image_key": "chip_thumbsup.png",
                "text": "That's it. How did it make you feel?",
                "button_text": "Finish",
            },
        ],
    },
    {
        "habit_key": "focus",
        "title": "Focus",
        "card_color": "#56AFFD",
        "activity_key": "three_deep_breaths",
        "activity_title": "3 deep breaths",
        "steps": [
            {
                "step_key": "big_breath_in",
                "order": 1,
                "image_key": "chip_arms_up.png",
                "text": "Take a big breath in",
                "button_text": "Breathe out",
            },
            {
                "step_key": "breathe_in",
                "order": 2,
                "image_key": "chip_standing.png",
                "text": "Breathe iiin",
                "button_text": "Breathe out",
            },
            {
                "step_key": "feel_the_calm",
                "order": 3,
                "image_key": "chip_thumbsup.png",
                "text": "...and breathe in and out one last time. Feel the calm.",
                "button_text": "Done",
            },
        ],
    },
]


def upgrade() -> None:
    op.add_column("habits", sa.Column("habit_key", sa.String(length=100), nullable=True))
    op.create_unique_constraint("uq_habits_habit_key", "habits", ["habit_key"])
    op.add_column("habits", sa.Column("card_color", sa.String(length=32), nullable=True))

    op.add_column("habit_steps", sa.Column("image_key", sa.String(length=200), nullable=True))
    op.add_column("habit_steps", sa.Column("button_text", sa.String(length=100), nullable=True))

    op.create_table(
        "child_habit_fridge_inventory",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("child_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("habit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fries", sa.Integer(), server_default="0", nullable=False),
        sa.Column("mussels", sa.Integer(), server_default="0", nullable=False),
        sa.Column("sardini", sa.Integer(), server_default="0", nullable=False),
        sa.Column("current_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_completed_date", sa.Date(), nullable=True),
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
        sa.ForeignKeyConstraint(["child_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["habit_id"], ["habits.id"]),
        sa.UniqueConstraint(
            "child_user_id",
            "habit_id",
            name="uq_child_habit_fridge_inventory_child_habit",
        ),
        sa.CheckConstraint("fries >= 0 AND fries <= 9", name="ck_child_habit_fridge_fries_range"),
        sa.CheckConstraint(
            "mussels >= 0 AND mussels <= 9",
            name="ck_child_habit_fridge_mussels_range",
        ),
        sa.CheckConstraint(
            "sardini >= 0 AND sardini <= 9",
            name="ck_child_habit_fridge_sardini_range",
        ),
        sa.CheckConstraint("current_streak >= 0", name="ck_child_habit_fridge_streak_nonneg"),
    )
    op.create_index(
        "ix_child_habit_fridge_inventory_child_user_id",
        "child_habit_fridge_inventory",
        ["child_user_id"],
    )
    op.create_index(
        "ix_child_habit_fridge_inventory_habit_id",
        "child_habit_fridge_inventory",
        ["habit_id"],
    )
    op.create_index(
        "ix_child_habit_fridge_inventory_child_habit",
        "child_habit_fridge_inventory",
        ["child_user_id", "habit_id"],
    )

    _seed_habit_tracker_catalog()


def _seed_habit_tracker_catalog() -> None:
    conn = op.get_bind()

    island_id = conn.execute(
        sa.text("SELECT id FROM islands WHERE island_name = :name LIMIT 1"),
        {"name": "Habit Tracker"},
    ).scalar()
    if island_id is None:
        island_id = uuid4()
        conn.execute(
            sa.text(
                """
                INSERT INTO islands (
                    id, island_name, status, display_order, comic_number, images_per_page
                ) VALUES (
                    :id, 'Habit Tracker', 'ACTIVE', 99, 99, 1
                )
                """
            ),
            {"id": island_id},
        )

    for order, item in enumerate(HABIT_CATALOG, start=1):
        existing_habit = conn.execute(
            sa.text("SELECT id FROM habits WHERE habit_key = :habit_key"),
            {"habit_key": item["habit_key"]},
        ).scalar()
        if existing_habit is not None:
            continue

        existing_sim = conn.execute(
            sa.text("SELECT id FROM simulations WHERE activity_key = :activity_key"),
            {"activity_key": item["activity_key"]},
        ).scalar()
        if existing_sim is not None:
            sim_id = existing_sim
        else:
            sim_id = uuid4()
            conn.execute(
                sa.text(
                    """
                    INSERT INTO simulations (
                        id, island_id, simulation_name, activity_key, simulation_type,
                        status, display_order
                    ) VALUES (
                        :id, :island_id, :name, :activity_key, 'HABIT',
                        'ACTIVE', :display_order
                    )
                    """
                ),
                {
                    "id": sim_id,
                    "island_id": island_id,
                    "name": item["activity_title"],
                    "activity_key": item["activity_key"],
                    "display_order": order,
                },
            )

        habit_id = uuid4()
        conn.execute(
            sa.text(
                """
                INSERT INTO habits (
                    id, simulation_id, habit_key, header_text, body_text, stars_to_earn,
                    habit_type, card_color, status
                ) VALUES (
                    :id, :sim_id, :habit_key, :header, :body, 1, 'DAILY', :card_color, 'ACTIVE'
                )
                """
            ),
            {
                "id": habit_id,
                "sim_id": sim_id,
                "habit_key": item["habit_key"],
                "header": item["title"],
                "body": item["title"],
                "card_color": item["card_color"],
            },
        )

        for step in item["steps"]:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO habit_steps (
                        id, habit_id, step_key, step_type, question, image_key,
                        button_text, display_order
                    ) VALUES (
                        :id, :habit_id, :step_key, 'instruction', :question, :image_key,
                        :button_text, :display_order
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "habit_id": habit_id,
                    "step_key": step["step_key"],
                    "question": step["text"],
                    "image_key": step["image_key"],
                    "button_text": step["button_text"],
                    "display_order": step["order"],
                },
            )


def downgrade() -> None:
    op.drop_index(
        "ix_child_habit_fridge_inventory_child_habit",
        table_name="child_habit_fridge_inventory",
    )
    op.drop_index(
        "ix_child_habit_fridge_inventory_habit_id",
        table_name="child_habit_fridge_inventory",
    )
    op.drop_index(
        "ix_child_habit_fridge_inventory_child_user_id",
        table_name="child_habit_fridge_inventory",
    )
    op.drop_table("child_habit_fridge_inventory")

    op.drop_column("habit_steps", "button_text")
    op.drop_column("habit_steps", "image_key")
    op.drop_constraint("uq_habits_habit_key", "habits", type_="unique")
    op.drop_column("habits", "card_color")
    op.drop_column("habits", "habit_key")
