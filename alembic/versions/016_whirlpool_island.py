"""whirlpool island content and progress tables

Revision ID: 016_whirlpool_island
Revises: 015_add_island_images_per_page
Create Date: 2026-07-31

"""

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "016_whirlpool_island"
down_revision: Union[str, None] = "015_add_island_images_per_page"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

WHIRLPOOL_ACTIVITY_KEYS = [
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
]


def _title_from_key(activity_key: str) -> str:
    return activity_key.replace("_", " ").replace(" s ", "'s ").title()


def upgrade() -> None:
    op.add_column("simulations", sa.Column("activity_key", sa.String(length=100), nullable=True))
    op.create_unique_constraint("uq_simulations_activity_key", "simulations", ["activity_key"])
    op.add_column("simulations", sa.Column("question_text", sa.Text(), nullable=True))
    op.add_column("simulations", sa.Column("correct_result_title", sa.String(length=200), nullable=True))
    op.add_column("simulations", sa.Column("correct_result_message", sa.Text(), nullable=True))
    op.add_column("simulations", sa.Column("wrong_result_title", sa.String(length=200), nullable=True))
    op.add_column("simulations", sa.Column("wrong_result_message", sa.Text(), nullable=True))

    op.add_column("simulation_answers", sa.Column("answer_key", sa.String(length=100), nullable=True))
    op.create_unique_constraint(
        "uq_simulation_answers_simulation_answer_key",
        "simulation_answers",
        ["simulation_id", "answer_key"],
    )

    op.add_column("habits", sa.Column("correct_result_title", sa.String(length=200), nullable=True))

    op.create_table(
        "habit_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("habit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_key", sa.String(length=100), nullable=False),
        sa.Column("step_type", sa.String(length=50), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["habit_id"], ["habits.id"]),
        sa.UniqueConstraint("habit_id", "step_key", name="uq_habit_steps_habit_step_key"),
    )
    op.create_index("ix_habit_steps_habit_id", "habit_steps", ["habit_id"])

    op.create_table(
        "habit_step_options",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("option_key", sa.String(length=100), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["step_id"], ["habit_steps.id"]),
        sa.UniqueConstraint("step_id", "option_key", name="uq_habit_step_options_step_option_key"),
    )
    op.create_index("ix_habit_step_options_step_id", "habit_step_options", ["step_id"])

    op.create_table(
        "child_simulation_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("child_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("simulation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("completed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
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
        sa.ForeignKeyConstraint(["child_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"]),
        sa.UniqueConstraint(
            "child_user_id",
            "simulation_id",
            name="uq_child_simulation_progress_child_simulation",
        ),
    )
    op.create_index(
        "ix_child_simulation_progress_child_user_id",
        "child_simulation_progress",
        ["child_user_id"],
    )
    op.create_index(
        "ix_child_simulation_progress_simulation_id",
        "child_simulation_progress",
        ["simulation_id"],
    )

    op.create_table(
        "child_island_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("child_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("island_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("completed", sa.Boolean(), server_default="false", nullable=False),
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
        sa.ForeignKeyConstraint(["child_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["island_id"], ["islands.id"]),
        sa.UniqueConstraint(
            "child_user_id",
            "island_id",
            name="uq_child_island_progress_child_island",
        ),
    )
    op.create_index(
        "ix_child_island_progress_child_user_id",
        "child_island_progress",
        ["child_user_id"],
    )
    op.create_index(
        "ix_child_island_progress_island_id",
        "child_island_progress",
        ["island_id"],
    )

    _seed_whirlpool_content()


def _seed_whirlpool_content() -> None:
    conn = op.get_bind()

    island_id = conn.execute(
        sa.text("SELECT id FROM islands WHERE comic_number = 0 LIMIT 1")
    ).scalar()

    if island_id is None:
        island_id = uuid4()
        conn.execute(
            sa.text(
                """
                INSERT INTO islands (
                    id, island_name, status, display_order, comic_number, images_per_page
                ) VALUES (
                    :id, 'Whirlpool', 'ACTIVE', 0, 0, 1
                )
                """
            ),
            {"id": island_id},
        )

    existing_keys = {
        row[0]
        for row in conn.execute(
            sa.text(
                "SELECT activity_key FROM simulations WHERE island_id = :island_id AND activity_key IS NOT NULL"
            ),
            {"island_id": island_id},
        ).fetchall()
    }

    for order, activity_key in enumerate(WHIRLPOOL_ACTIVITY_KEYS, start=1):
        if activity_key in existing_keys:
            continue

        sim_id = uuid4()

        if activity_key == "one_more_sign":
            conn.execute(
                sa.text(
                    """
                    INSERT INTO simulations (
                        id, island_id, simulation_name, activity_key, simulation_type,
                        question_text, correct_result_title, correct_result_message,
                        wrong_result_title, wrong_result_message, status, display_order
                    ) VALUES (
                        :id, :island_id, :name, :activity_key, 'SCRIPT',
                        :question_text, :crt, :crm, :wrt, :wrm, 'ACTIVE', :display_order
                    )
                    """
                ),
                {
                    "id": sim_id,
                    "island_id": island_id,
                    "name": "Scenario: One more",
                    "activity_key": activity_key,
                    "question_text": (
                        "Your parent asked you to finish your game and log off..."
                    ),
                    "crt": "Nice! You kept your plan and your mate.",
                    "crm": "Do not let the game decide when you stop.",
                    "wrt": "It is just one more game — right?",
                    "wrm": "That is exactly what the whirlpool would whisper...",
                    "display_order": order,
                },
            )
            conn.execute(
                sa.text(
                    """
                    INSERT INTO simulation_answers (
                        id, simulation_id, option_number, answer_key, answer, is_correct
                    ) VALUES
                    (:id1, :sim_id, 1, 'log-off-anyway',
                     'Log off anyway — gotta go, play tomorrow?', true),
                    (:id2, :sim_id, 2, 'just-one-more',
                     'Just one more. It is only one game.', false)
                    """
                ),
                {"id1": uuid4(), "id2": uuid4(), "sim_id": sim_id},
            )
        elif activity_key == "stop_star_fish":
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
                    "name": "Screen-free sanctuary",
                    "activity_key": activity_key,
                    "display_order": order,
                },
            )
            habit_id = uuid4()
            conn.execute(
                sa.text(
                    """
                    INSERT INTO habits (
                        id, simulation_id, header_text, body_text, stars_to_earn,
                        habit_type, correct_result_title, status
                    ) VALUES (
                        :id, :sim_id, :header, :body, 1, 'SETUP', :crt, 'ACTIVE'
                    )
                    """
                ),
                {
                    "id": habit_id,
                    "sim_id": sim_id,
                    "header": "Screen-free sanctuary",
                    "body": "Set a place in your home that is a screen-free sanctuary.",
                    "crt": "Now, stick a sign on the door or wall so your family knows.",
                },
            )
            step_id = uuid4()
            conn.execute(
                sa.text(
                    """
                    INSERT INTO habit_steps (
                        id, habit_id, step_key, step_type, question, display_order
                    ) VALUES (
                        :id, :habit_id, 'choose-room', 'single-choice', 'Pick a room', 1
                    )
                    """
                ),
                {"id": step_id, "habit_id": habit_id},
            )
            conn.execute(
                sa.text(
                    """
                    INSERT INTO habit_step_options (
                        id, step_id, option_key, label, display_order
                    ) VALUES (
                        :id, :step_id, 'bedroom', 'Someone''s bedroom', 1
                    )
                    """
                ),
                {"id": uuid4(), "step_id": step_id},
            )
        else:
            title = _title_from_key(activity_key)
            conn.execute(
                sa.text(
                    """
                    INSERT INTO simulations (
                        id, island_id, simulation_name, activity_key, simulation_type,
                        question_text, correct_result_title, correct_result_message,
                        wrong_result_title, wrong_result_message, status, display_order
                    ) VALUES (
                        :id, :island_id, :name, :activity_key, 'SCRIPT',
                        :question_text, :crt, :crm, :wrt, :wrm, 'ACTIVE', :display_order
                    )
                    """
                ),
                {
                    "id": sim_id,
                    "island_id": island_id,
                    "name": title,
                    "activity_key": activity_key,
                    "question_text": f"Placeholder question for {title}.",
                    "crt": "Nice work!",
                    "crm": "You completed this activity.",
                    "wrt": "Try again",
                    "wrm": "Give it another go.",
                    "display_order": order,
                },
            )
            conn.execute(
                sa.text(
                    """
                    INSERT INTO simulation_answers (
                        id, simulation_id, option_number, answer_key, answer, is_correct
                    ) VALUES (
                        :id, :sim_id, 1, 'placeholder-correct', 'Continue', true
                    )
                    """
                ),
                {"id": uuid4(), "sim_id": sim_id},
            )


def downgrade() -> None:
    op.drop_index("ix_child_island_progress_island_id", table_name="child_island_progress")
    op.drop_index("ix_child_island_progress_child_user_id", table_name="child_island_progress")
    op.drop_table("child_island_progress")

    op.drop_index(
        "ix_child_simulation_progress_simulation_id",
        table_name="child_simulation_progress",
    )
    op.drop_index(
        "ix_child_simulation_progress_child_user_id",
        table_name="child_simulation_progress",
    )
    op.drop_table("child_simulation_progress")

    op.drop_index("ix_habit_step_options_step_id", table_name="habit_step_options")
    op.drop_table("habit_step_options")

    op.drop_index("ix_habit_steps_habit_id", table_name="habit_steps")
    op.drop_table("habit_steps")

    op.drop_column("habits", "correct_result_title")

    op.drop_constraint(
        "uq_simulation_answers_simulation_answer_key",
        "simulation_answers",
        type_="unique",
    )
    op.drop_column("simulation_answers", "answer_key")

    op.drop_column("simulations", "wrong_result_message")
    op.drop_column("simulations", "wrong_result_title")
    op.drop_column("simulations", "correct_result_message")
    op.drop_column("simulations", "correct_result_title")
    op.drop_column("simulations", "question_text")
    op.drop_constraint("uq_simulations_activity_key", "simulations", type_="unique")
    op.drop_column("simulations", "activity_key")
