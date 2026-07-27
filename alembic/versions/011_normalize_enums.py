"""normalize enum values to PDF uppercase

Revision ID: 011_normalize_enums
Revises: 010_migrate_promo_to_vouchers
Create Date: 2026-07-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_normalize_enums"
down_revision: Union[str, None] = "010_promo_to_vouchers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ENUM_MIGRATIONS = [
    (
        "user_type",
        "users",
        "user_type",
        {
            "Parent": "PARENT",
            "Child": "CHILD",
            "Teacher": "TEACHER",
            "Guardian": "GUARDIAN",
        },
        ["PARENT", "CHILD", "TEACHER", "GUARDIAN"],
    ),
    (
        "age_cohort",
        "users",
        "age_cohort",
        {
            "Toddler": "TODDLER",
            "Child": "CHILD",
            "Tween": "TWEEN",
            "Teen": "TEEN",
            "Adult": "ADULT",
        },
        ["TODDLER", "CHILD", "TWEEN", "TEEN", "ADULT"],
    ),
    (
        "user_status",
        "users",
        "status",
        {
            "Active": "ACTIVE",
            "Inactive": "INACTIVE",
            "Suspended": "SUSPENDED",
        },
        ["ACTIVE", "INACTIVE", "SUSPENDED"],
    ),
]


def _migrate_enum(enum_name: str, table: str, column: str, mapping: dict[str, str], values: list[str]) -> None:
    temp_enum = f"{enum_name}_new"
    values_sql = ", ".join(f"'{value}'" for value in values)
    op.execute(sa.text(f"CREATE TYPE {temp_enum} AS ENUM ({values_sql})"))
    op.execute(sa.text(f"ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT"))
    op.execute(
        sa.text(
            f"""
            ALTER TABLE {table}
            ALTER COLUMN {column} TYPE {temp_enum}
            USING (
                CASE {column}::text
                """
            + " ".join(f"WHEN '{old}' THEN '{new}'::{temp_enum}" for old, new in mapping.items())
            + f"""
                ELSE {column}::text::{temp_enum}
                END
            )
            """
        )
    )
    op.execute(sa.text(f"DROP TYPE {enum_name}"))
    op.execute(sa.text(f"ALTER TYPE {temp_enum} RENAME TO {enum_name}"))


def upgrade() -> None:
    for enum_name, table, column, mapping, values in _ENUM_MIGRATIONS:
        _migrate_enum(enum_name, table, column, mapping, values)

    op.execute(sa.text("ALTER TABLE users ALTER COLUMN status SET DEFAULT 'ACTIVE'"))
    op.execute(sa.text("ALTER TABLE users ALTER COLUMN user_type SET DEFAULT 'PARENT'"))


def downgrade() -> None:
    reverse_migrations = [
        (
            "user_type",
            "users",
            "user_type",
            {
                "PARENT": "Parent",
                "CHILD": "Child",
                "TEACHER": "Teacher",
                "GUARDIAN": "Guardian",
            },
            ["Parent", "Child", "Teacher", "Guardian"],
        ),
        (
            "age_cohort",
            "users",
            "age_cohort",
            {
                "TODDLER": "Toddler",
                "CHILD": "Child",
                "TWEEN": "Tween",
                "TEEN": "Teen",
                "ADULT": "Adult",
            },
            ["Toddler", "Child", "Tween", "Teen", "Adult"],
        ),
        (
            "user_status",
            "users",
            "status",
            {
                "ACTIVE": "Active",
                "INACTIVE": "Inactive",
                "SUSPENDED": "Suspended",
            },
            ["Active", "Inactive", "Suspended"],
        ),
    ]
    for enum_name, table, column, mapping, values in reverse_migrations:
        _migrate_enum(enum_name, table, column, mapping, values)

    op.execute(sa.text("ALTER TABLE users ALTER COLUMN status SET DEFAULT 'Active'"))
    op.execute(sa.text("ALTER TABLE users ALTER COLUMN user_type SET DEFAULT 'Parent'"))
