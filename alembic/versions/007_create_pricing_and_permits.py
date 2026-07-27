"""create pricing, vouchers, and learner permit tables

Revision ID: 007_create_pricing_and_permits
Revises: 006_create_content_and_rewards_tables
Create Date: 2026-07-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007_pricing_permits"
down_revision: Union[str, None] = "006_content_rewards"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

billing_interval = postgresql.ENUM("MONTHLY", "YEARLY", "ONE_TIME", name="billing_interval", create_type=False)
discount_type = postgresql.ENUM("PERCENTAGE", "FIXED_AMOUNT", name="discount_type", create_type=False)
learner_permit_status = postgresql.ENUM(
    "ACTIVE", "EXPIRED", "REVOKED", name="learner_permit_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM("MONTHLY", "YEARLY", "ONE_TIME", name="billing_interval").create(bind, checkfirst=True)
    postgresql.ENUM("PERCENTAGE", "FIXED_AMOUNT", name="discount_type").create(bind, checkfirst=True)
    postgresql.ENUM("ACTIVE", "EXPIRED", "REVOKED", name="learner_permit_status").create(bind, checkfirst=True)

    op.create_table(
        "pricing_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("plan_name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency_code", sa.CHAR(length=3), nullable=False),
        sa.Column("billing_interval", billing_interval, nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
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
        sa.UniqueConstraint("plan_name", name="uq_pricing_plans_plan_name"),
        sa.CheckConstraint("price_amount >= 0", name="ck_pricing_plans_price_amount_nonneg"),
    )

    op.create_table(
        "vouchers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("discount_type", discount_type, nullable=False),
        sa.Column("discount_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency_code", sa.CHAR(length=3), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_redemptions", sa.Integer(), nullable=True),
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
        sa.UniqueConstraint("code", name="uq_vouchers_code"),
        sa.CheckConstraint("discount_value > 0", name="ck_vouchers_discount_value_positive"),
        sa.CheckConstraint(
            "max_redemptions IS NULL OR max_redemptions > 0",
            name="ck_vouchers_max_redemptions_positive",
        ),
    )
    op.create_index("ix_vouchers_code", "vouchers", ["code"])

    op.create_table(
        "voucher_pricing_plans",
        sa.Column("voucher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pricing_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["voucher_id"], ["vouchers.id"]),
        sa.ForeignKeyConstraint(["pricing_plan_id"], ["pricing_plans.id"]),
        sa.PrimaryKeyConstraint("voucher_id", "pricing_plan_id"),
    )
    op.create_index("ix_voucher_pricing_plans_pricing_plan_id", "voucher_pricing_plans", ["pricing_plan_id"])

    op.create_table(
        "voucher_redemptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("voucher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "redeemed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["voucher_id"], ["vouchers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_voucher_redemptions_voucher_id", "voucher_redemptions", ["voucher_id"])
    op.create_index("ix_voucher_redemptions_user_id", "voucher_redemptions", ["user_id"])

    op.create_table(
        "learner_permits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("licence_number", sa.String(length=50), nullable=False),
        sa.Column("icon_url", sa.Text(), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", learner_permit_status, nullable=False),
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
        sa.UniqueConstraint("user_id", name="uq_learner_permits_user_id"),
        sa.UniqueConstraint("licence_number", name="uq_learner_permits_licence_number"),
    )
    op.create_index("ix_learner_permits_user_id", "learner_permits", ["user_id"])

    op.create_table(
        "learner_permit_badges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("learner_permit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("island_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["learner_permit_id"], ["learner_permits.id"]),
        sa.ForeignKeyConstraint(["island_id"], ["islands.id"]),
        sa.UniqueConstraint(
            "learner_permit_id",
            "island_id",
            name="uq_learner_permit_badges_permit_island",
        ),
    )
    op.create_index("ix_learner_permit_badges_learner_permit_id", "learner_permit_badges", ["learner_permit_id"])
    op.create_index("ix_learner_permit_badges_island_id", "learner_permit_badges", ["island_id"])

    op.execute(
        sa.text(
            """
            INSERT INTO pricing_plans (id, plan_name, description, price_amount, currency_code, billing_interval, active)
            VALUES
                (gen_random_uuid(), 'Monthly', 'Monthly subscription', 15.99, 'USD', 'MONTHLY', true),
                (gen_random_uuid(), 'Yearly', 'Yearly subscription', 149.49, 'USD', 'YEARLY', true)
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_learner_permit_badges_island_id", table_name="learner_permit_badges")
    op.drop_index("ix_learner_permit_badges_learner_permit_id", table_name="learner_permit_badges")
    op.drop_table("learner_permit_badges")
    op.drop_index("ix_learner_permits_user_id", table_name="learner_permits")
    op.drop_table("learner_permits")
    op.drop_index("ix_voucher_redemptions_user_id", table_name="voucher_redemptions")
    op.drop_index("ix_voucher_redemptions_voucher_id", table_name="voucher_redemptions")
    op.drop_table("voucher_redemptions")
    op.drop_index("ix_voucher_pricing_plans_pricing_plan_id", table_name="voucher_pricing_plans")
    op.drop_table("voucher_pricing_plans")
    op.drop_index("ix_vouchers_code", table_name="vouchers")
    op.drop_table("vouchers")
    op.drop_table("pricing_plans")

    bind = op.get_bind()
    postgresql.ENUM(name="learner_permit_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="discount_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="billing_interval").drop(bind, checkfirst=True)
