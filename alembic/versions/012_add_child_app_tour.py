"""add child_app_tour to users

Revision ID: 012_add_child_app_tour
Revises: 011_normalize_enums
Create Date: 2026-07-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_add_child_app_tour"
down_revision: Union[str, None] = "011_normalize_enums"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("child_app_tour", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("users", "child_app_tour")
