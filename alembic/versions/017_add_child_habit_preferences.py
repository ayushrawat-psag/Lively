"""add child habit preferences table

Revision ID: 017_add_child_habit_preferences
Revises: 016_whirlpool_island
Create Date: 2026-08-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "017_add_child_habit_preferences"
down_revision: Union[str, None] = "016_whirlpool_island"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "child_habit_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("child_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("habit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("default_activity_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.ForeignKeyConstraint(["default_activity_id"], ["simulations.id"]),
        sa.UniqueConstraint(
            "child_user_id",
            "habit_id",
            name="uq_child_habit_preferences_child_habit",
        ),
    )
    op.create_index(
        "ix_child_habit_preferences_child_user_id",
        "child_habit_preferences",
        ["child_user_id"],
    )
    op.create_index(
        "ix_child_habit_preferences_habit_id",
        "child_habit_preferences",
        ["habit_id"],
    )
    op.create_index(
        "ix_child_habit_preferences_child_habit",
        "child_habit_preferences",
        ["child_user_id", "habit_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_child_habit_preferences_child_habit",
        table_name="child_habit_preferences",
    )
    op.drop_index(
        "ix_child_habit_preferences_habit_id",
        table_name="child_habit_preferences",
    )
    op.drop_index(
        "ix_child_habit_preferences_child_user_id",
        table_name="child_habit_preferences",
    )
    op.drop_table("child_habit_preferences")
