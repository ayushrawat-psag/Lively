"""migrate children into users and drop children table

Revision ID: 009_migrate_children_to_users
Revises: 008_create_user_activity
Create Date: 2026-07-27

"""

import json
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from app.core.invite_code import generate_invite_code

revision: str = "009_children_to_users"
down_revision: Union[str, None] = "008_user_activity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _generate_family_invite_code() -> str:
    return generate_invite_code()


def upgrade() -> None:
    bind = op.get_bind()
    children = bind.execute(
        sa.text(
            """
            SELECT id, parent_user_id, name, date_of_birth, gender, devices,
                   pin_hash, onboarding, deleted_at, created_at, updated_at
            FROM children
            """
        )
    ).fetchall()

    parent_families: dict[uuid.UUID, uuid.UUID] = {}

    for child in children:
        parent_id = child.parent_user_id
        family_id = parent_families.get(parent_id)

        if family_id is None:
            existing_family = bind.execute(
                sa.text("SELECT id FROM families WHERE primary_parent_user_id = :parent_id"),
                {"parent_id": parent_id},
            ).first()

            if existing_family:
                family_id = existing_family.id
            else:
                family_id = uuid.uuid4()
                invite_code = _generate_family_invite_code()
                while bind.execute(
                    sa.text("SELECT 1 FROM families WHERE invite_code = :code"),
                    {"code": invite_code},
                ).first():
                    invite_code = _generate_family_invite_code()

                bind.execute(
                    sa.text(
                        """
                        INSERT INTO families (
                            id, family_name, primary_parent_user_id, invite_code, created_at, updated_at
                        )
                        VALUES (:id, NULL, :parent_id, :invite_code, now(), now())
                        """
                    ),
                    {"id": family_id, "parent_id": parent_id, "invite_code": invite_code},
                )

                bind.execute(
                    sa.text("UPDATE users SET family_id = :family_id WHERE id = :parent_id"),
                    {"family_id": family_id, "parent_id": parent_id},
                )

            parent_families[parent_id] = family_id

        name_parts = (child.name or "").strip().split(None, 1)
        first_name = name_parts[0] if name_parts else "Child"
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        bind.execute(
            sa.text(
                """
                INSERT INTO users (
                    id, user_type, first_name, last_name, email, password_hash, pin_hash,
                    date_of_birth, age_cohort, is_child, invite_code, family_id, school_id,
                    classroom_id, status, email_verified, accepted_terms, gender, devices,
                    onboarding, deleted_at, created_at, updated_at
                )
                VALUES (
                    :id, 'Child', :first_name, :last_name, NULL, NULL, :pin_hash,
                    :date_of_birth, NULL, true, NULL, :family_id, NULL,
                    NULL, 'Active', false, false, :gender, CAST(:devices AS jsonb),
                    :onboarding, :deleted_at, :created_at, :updated_at
                )
                """
            ),
            {
                "id": child.id,
                "first_name": first_name,
                "last_name": last_name,
                "pin_hash": child.pin_hash,
                "date_of_birth": child.date_of_birth,
                "family_id": family_id,
                "gender": child.gender,
                "devices": json.dumps(child.devices if child.devices is not None else []),
                "onboarding": child.onboarding,
                "deleted_at": child.deleted_at,
                "created_at": child.created_at,
                "updated_at": child.updated_at,
            },
        )

    op.drop_index("ix_children_parent_user_id", table_name="children")
    op.drop_table("children")


def downgrade() -> None:
    op.create_table(
        "children",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("parent_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("gender", sa.String(length=32), nullable=False),
        sa.Column(
            "devices",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("pin_hash", sa.Text(), nullable=True),
        sa.Column("onboarding", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["parent_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_children_parent_user_id", "children", ["parent_user_id"])

    bind = op.get_bind()
    child_users = bind.execute(
        sa.text(
            """
            SELECT u.id, u.first_name, u.last_name, u.date_of_birth, u.gender, u.devices,
                   u.pin_hash, u.onboarding, u.deleted_at, u.created_at, u.updated_at,
                   f.primary_parent_user_id
            FROM users u
            JOIN families f ON u.family_id = f.id
            WHERE u.is_child = true
            """
        )
    ).fetchall()

    for child in child_users:
        name = child.first_name
        if child.last_name:
            name = f"{child.first_name} {child.last_name}".strip()
        bind.execute(
            sa.text(
                """
                INSERT INTO children (
                    id, parent_user_id, name, date_of_birth, gender, devices,
                    pin_hash, onboarding, deleted_at, created_at, updated_at
                )
                VALUES (
                    :id, :parent_user_id, :name, :date_of_birth, :gender, :devices,
                    :pin_hash, :onboarding, :deleted_at, :created_at, :updated_at
                )
                """
            ),
            {
                "id": child.id,
                "parent_user_id": child.primary_parent_user_id,
                "name": name,
                "date_of_birth": child.date_of_birth,
                "gender": child.gender or "",
                "devices": child.devices,
                "pin_hash": child.pin_hash,
                "onboarding": child.onboarding,
                "deleted_at": child.deleted_at,
                "created_at": child.created_at,
                "updated_at": child.updated_at,
            },
        )
        bind.execute(sa.text("DELETE FROM users WHERE id = :id"), {"id": child.id})
