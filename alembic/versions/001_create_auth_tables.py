"""create auth tables

Revision ID: 001_create_auth_tables
Revises:
Create Date: 2026-07-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_create_auth_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_type = postgresql.ENUM(
    "Parent", "Child", "Teacher", "Guardian", name="user_type", create_type=False
)
age_cohort = postgresql.ENUM(
    "Toddler", "Child", "Tween", "Teen", "Adult", name="age_cohort", create_type=False
)
user_status = postgresql.ENUM(
    "Active", "Inactive", "Suspended", name="user_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(
        "Parent", "Child", "Teacher", "Guardian", name="user_type"
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "Toddler", "Child", "Tween", "Teen", "Adult", name="age_cohort"
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "Active", "Inactive", "Suspended", name="user_status"
    ).create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_type", user_type, nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("pin_hash", sa.Text(), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("age_cohort", age_cohort, nullable=True),
        sa.Column("is_child", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("invite_code", sa.String(length=20), nullable=True),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", user_status, nullable=False),
        sa.Column("email_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("accepted_terms", sa.Boolean(), server_default="false", nullable=False),
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
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "email_verification_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_used", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_email_verification_codes_user_id",
        "email_verification_codes",
        ["user_id"],
    )
    op.create_index(
        "ix_email_verification_codes_email",
        "email_verification_codes",
        ["email"],
    )


def downgrade() -> None:
    op.drop_index("ix_email_verification_codes_email", table_name="email_verification_codes")
    op.drop_index("ix_email_verification_codes_user_id", table_name="email_verification_codes")
    op.drop_table("email_verification_codes")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    postgresql.ENUM(name="user_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="age_cohort").drop(bind, checkfirst=True)
    postgresql.ENUM(name="user_type").drop(bind, checkfirst=True)
