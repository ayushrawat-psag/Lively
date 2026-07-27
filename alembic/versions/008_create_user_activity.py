"""create user_activity and migrate last_login_at

Revision ID: 008_create_user_activity
Revises: 007_create_pricing_and_permits
Create Date: 2026-07-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008_user_activity"
down_revision: Union[str, None] = "007_pricing_permits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_activity",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("device_type", sa.String(length=100), nullable=True),
        sa.Column("mac_address", sa.String(length=17), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("last_completed_simulation_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["last_completed_simulation_id"], ["simulations.id"]),
        sa.UniqueConstraint("user_id", name="uq_user_activity_user_id"),
    )
    op.create_index("ix_user_activity_user_id", "user_activity", ["user_id"])
    op.create_index(
        "ix_user_activity_last_completed_simulation_id",
        "user_activity",
        ["last_completed_simulation_id"],
    )

    op.execute(
        sa.text(
            """
            INSERT INTO user_activity (id, user_id, last_login_at, created_at, updated_at)
            SELECT gen_random_uuid(), id, last_login_at, now(), now()
            FROM users
            WHERE last_login_at IS NOT NULL
            """
        )
    )

    op.drop_column("users", "last_login_at")


def downgrade() -> None:
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE users u
            SET last_login_at = ua.last_login_at
            FROM user_activity ua
            WHERE ua.user_id = u.id
            """
        )
    )
    op.drop_index("ix_user_activity_last_completed_simulation_id", table_name="user_activity")
    op.drop_index("ix_user_activity_user_id", table_name="user_activity")
    op.drop_table("user_activity")
