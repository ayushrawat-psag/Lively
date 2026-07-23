"""create promo_codes and promo_code_redemptions

Revision ID: 003_create_promo_codes
Revises: 002_unique_invite_code
Create Date: 2026-07-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_create_promo_codes"
down_revision: Union[str, None] = "002_unique_invite_code"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "promo_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_redemptions", sa.Integer(), nullable=True),
        sa.Column("max_redemptions_per_user", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("code", name="uq_promo_codes_code"),
    )
    op.create_index("ix_promo_codes_code", "promo_codes", ["code"])

    op.create_table(
        "promo_code_redemptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("promo_code_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "redeemed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["promo_code_id"],
            ["promo_codes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_promo_code_redemptions_promo_code_id",
        "promo_code_redemptions",
        ["promo_code_id"],
    )
    op.create_index(
        "ix_promo_code_redemptions_user_id",
        "promo_code_redemptions",
        ["user_id"],
    )

    # Sample promo for QA / mobile testing (20% off, one redemption per user).
    op.execute(
        sa.text(
            """
            INSERT INTO promo_codes (
                id, code, discount_percent, is_active, max_redemptions_per_user
            ) VALUES (
                gen_random_uuid(), 'LIVELY20', 20, true, 1
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_promo_code_redemptions_user_id", table_name="promo_code_redemptions")
    op.drop_index("ix_promo_code_redemptions_promo_code_id", table_name="promo_code_redemptions")
    op.drop_table("promo_code_redemptions")
    op.drop_index("ix_promo_codes_code", table_name="promo_codes")
    op.drop_table("promo_codes")
