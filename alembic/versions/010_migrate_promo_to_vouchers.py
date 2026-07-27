"""migrate promo codes to vouchers

Revision ID: 010_migrate_promo_to_vouchers
Revises: 009_migrate_children_to_users
Create Date: 2026-07-27

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_promo_to_vouchers"
down_revision: Union[str, None] = "009_children_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vouchers", sa.Column("max_redemptions_per_user", sa.Integer(), nullable=True))

    bind = op.get_bind()
    promos = bind.execute(
        sa.text(
            """
            SELECT id, code, discount_percent, is_active, starts_at, expires_at,
                   max_redemptions, max_redemptions_per_user
            FROM promo_codes
            """
        )
    ).fetchall()

    plan_ids = [
        row.id
        for row in bind.execute(sa.text("SELECT id FROM pricing_plans WHERE active = true")).fetchall()
    ]

    promo_to_voucher: dict[uuid.UUID, uuid.UUID] = {}

    for promo in promos:
        voucher_id = uuid.uuid4()
        promo_to_voucher[promo.id] = voucher_id
        bind.execute(
            sa.text(
                """
                INSERT INTO vouchers (
                    id, code, discount_type, discount_value, currency_code, active,
                    valid_from, valid_until, max_redemptions, max_redemptions_per_user,
                    created_at, updated_at
                )
                VALUES (
                    :id, :code, 'PERCENTAGE', :discount_value, NULL, :active,
                    :valid_from, :valid_until, :max_redemptions, :max_redemptions_per_user,
                    now(), now()
                )
                """
            ),
            {
                "id": voucher_id,
                "code": promo.code,
                "discount_value": promo.discount_percent,
                "active": promo.is_active,
                "valid_from": promo.starts_at,
                "valid_until": promo.expires_at,
                "max_redemptions": promo.max_redemptions,
                "max_redemptions_per_user": promo.max_redemptions_per_user,
            },
        )
        for plan_id in plan_ids:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO voucher_pricing_plans (voucher_id, pricing_plan_id, created_at)
                    VALUES (:voucher_id, :plan_id, now())
                    """
                ),
                {"voucher_id": voucher_id, "plan_id": plan_id},
            )

    redemptions = bind.execute(
        sa.text("SELECT promo_code_id, user_id, redeemed_at FROM promo_code_redemptions")
    ).fetchall()
    for redemption in redemptions:
        voucher_id = promo_to_voucher.get(redemption.promo_code_id)
        if voucher_id is None:
            continue
        bind.execute(
            sa.text(
                """
                INSERT INTO voucher_redemptions (id, voucher_id, user_id, redeemed_at)
                VALUES (gen_random_uuid(), :voucher_id, :user_id, :redeemed_at)
                """
            ),
            {
                "voucher_id": voucher_id,
                "user_id": redemption.user_id,
                "redeemed_at": redemption.redeemed_at,
            },
        )

    op.drop_index("ix_promo_code_redemptions_user_id", table_name="promo_code_redemptions")
    op.drop_index("ix_promo_code_redemptions_promo_code_id", table_name="promo_code_redemptions")
    op.drop_table("promo_code_redemptions")
    op.drop_index("ix_promo_codes_code", table_name="promo_codes")
    op.drop_table("promo_codes")


def downgrade() -> None:
    op.create_table(
        "promo_codes",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_redemptions", sa.Integer(), nullable=True),
        sa.Column("max_redemptions_per_user", sa.Integer(), nullable=True),
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
        sa.UniqueConstraint("code", name="uq_promo_codes_code"),
    )
    op.create_index("ix_promo_codes_code", "promo_codes", ["code"], unique=True)

    op.create_table(
        "promo_code_redemptions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("promo_code_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "redeemed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["promo_code_id"], ["promo_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_promo_code_redemptions_promo_code_id", "promo_code_redemptions", ["promo_code_id"])
    op.create_index("ix_promo_code_redemptions_user_id", "promo_code_redemptions", ["user_id"])

    bind = op.get_bind()
    vouchers = bind.execute(
        sa.text(
            """
            SELECT id, code, discount_value, active, valid_from, valid_until,
                   max_redemptions, max_redemptions_per_user
            FROM vouchers
            WHERE discount_type = 'PERCENTAGE'
            """
        )
    ).fetchall()

    voucher_to_promo: dict[uuid.UUID, uuid.UUID] = {}
    for voucher in vouchers:
        promo_id = uuid.uuid4()
        voucher_to_promo[voucher.id] = promo_id
        bind.execute(
            sa.text(
                """
                INSERT INTO promo_codes (
                    id, code, discount_percent, is_active, starts_at, expires_at,
                    max_redemptions, max_redemptions_per_user, created_at, updated_at
                )
                VALUES (
                    :id, :code, :discount_percent, :active, :valid_from, :valid_until,
                    :max_redemptions, :max_redemptions_per_user, now(), now()
                )
                """
            ),
            {
                "id": promo_id,
                "code": voucher.code,
                "discount_percent": int(voucher.discount_value),
                "active": voucher.active,
                "valid_from": voucher.valid_from,
                "valid_until": voucher.valid_until,
                "max_redemptions": voucher.max_redemptions,
                "max_redemptions_per_user": voucher.max_redemptions_per_user,
            },
        )

    redemptions = bind.execute(
        sa.text("SELECT voucher_id, user_id, redeemed_at FROM voucher_redemptions")
    ).fetchall()
    for redemption in redemptions:
        promo_id = voucher_to_promo.get(redemption.voucher_id)
        if promo_id is None:
            continue
        bind.execute(
            sa.text(
                """
                INSERT INTO promo_code_redemptions (id, promo_code_id, user_id, redeemed_at)
                VALUES (gen_random_uuid(), :promo_code_id, :user_id, :redeemed_at)
                """
            ),
            {
                "promo_code_id": promo_id,
                "user_id": redemption.user_id,
                "redeemed_at": redemption.redeemed_at,
            },
        )

    op.drop_column("vouchers", "max_redemptions_per_user")
