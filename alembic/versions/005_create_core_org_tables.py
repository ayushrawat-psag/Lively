"""create core org tables and user child extension columns

Revision ID: 005_create_core_org_tables
Revises: 004_create_children
Create Date: 2026-07-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_core_org"
down_revision: Union[str, None] = "004_create_children"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "families",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("family_name", sa.String(length=150), nullable=True),
        sa.Column("primary_parent_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("secondary_parent_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("invite_code", sa.String(length=20), nullable=False),
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
        sa.ForeignKeyConstraint(["primary_parent_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["secondary_parent_user_id"], ["users.id"]),
        sa.UniqueConstraint("invite_code", name="uq_families_invite_code"),
    )
    op.create_index("ix_families_primary_parent_user_id", "families", ["primary_parent_user_id"])
    op.create_index("ix_families_secondary_parent_user_id", "families", ["secondary_parent_user_id"])

    op.create_table(
        "schools",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("school_name", sa.String(length=255), nullable=False),
        sa.Column("school_admin_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invite_code", sa.String(length=20), nullable=False),
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
        sa.ForeignKeyConstraint(["school_admin_user_id"], ["users.id"]),
        sa.UniqueConstraint("invite_code", name="uq_schools_invite_code"),
    )
    op.create_index("ix_schools_school_admin_user_id", "schools", ["school_admin_user_id"])

    op.create_table(
        "classrooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("classroom_name", sa.String(length=100), nullable=False),
        sa.Column("teacher_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invite_code", sa.String(length=20), nullable=False),
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
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["teacher_user_id"], ["users.id"]),
        sa.UniqueConstraint("invite_code", name="uq_classrooms_invite_code"),
    )
    op.create_index("ix_classrooms_school_id", "classrooms", ["school_id"])
    op.create_index("ix_classrooms_teacher_user_id", "classrooms", ["teacher_user_id"])

    op.create_foreign_key(
        "fk_users_family_id_families",
        "users",
        "families",
        ["family_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_users_school_id_schools",
        "users",
        "schools",
        ["school_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_users_classroom_id_classrooms",
        "users",
        "classrooms",
        ["classroom_id"],
        ["id"],
    )
    op.create_index("ix_users_family_id", "users", ["family_id"])
    op.create_index("ix_users_school_id", "users", ["school_id"])
    op.create_index("ix_users_classroom_id", "users", ["classroom_id"])

    op.add_column("users", sa.Column("gender", sa.String(length=32), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "devices",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "users",
        sa.Column("onboarding", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "onboarding")
    op.drop_column("users", "devices")
    op.drop_column("users", "gender")
    op.drop_index("ix_users_classroom_id", table_name="users")
    op.drop_index("ix_users_school_id", table_name="users")
    op.drop_index("ix_users_family_id", table_name="users")
    op.drop_constraint("fk_users_classroom_id_classrooms", "users", type_="foreignkey")
    op.drop_constraint("fk_users_school_id_schools", "users", type_="foreignkey")
    op.drop_constraint("fk_users_family_id_families", "users", type_="foreignkey")
    op.drop_index("ix_classrooms_teacher_user_id", table_name="classrooms")
    op.drop_index("ix_classrooms_school_id", table_name="classrooms")
    op.drop_table("classrooms")
    op.drop_index("ix_schools_school_admin_user_id", table_name="schools")
    op.drop_table("schools")
    op.drop_index("ix_families_secondary_parent_user_id", table_name="families")
    op.drop_index("ix_families_primary_parent_user_id", table_name="families")
    op.drop_table("families")
