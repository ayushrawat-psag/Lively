"""add unique constraint on users.invite_code

Revision ID: 002_unique_invite_code
Revises: 001_create_auth_tables
Create Date: 2026-07-23

"""

from typing import Sequence, Union

from alembic import op

revision: str = "002_unique_invite_code"
down_revision: Union[str, None] = "001_create_auth_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_users_invite_code", "users", ["invite_code"])


def downgrade() -> None:
    op.drop_constraint("uq_users_invite_code", "users", type_="unique")
