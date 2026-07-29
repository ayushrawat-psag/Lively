"""create comic pages table

Revision ID: 013_create_comic_pages
Revises: 012_add_child_app_tour
Create Date: 2026-07-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013_create_comic_pages"
down_revision: Union[str, None] = "012_add_child_app_tour"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

content_status = postgresql.ENUM("ACTIVE", "INACTIVE", name="content_status", create_type=False)


def upgrade() -> None:
    op.create_table(
        "comic_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("island_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("status", content_status, nullable=False),
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
        sa.ForeignKeyConstraint(["island_id"], ["islands.id"]),
        sa.CheckConstraint("display_order > 0", name="ck_comic_pages_display_order_positive"),
        sa.UniqueConstraint(
            "island_id",
            "display_order",
            name="uq_comic_pages_island_display_order",
        ),
    )
    op.create_index("ix_comic_pages_island_id", "comic_pages", ["island_id"])


def downgrade() -> None:
    op.drop_index("ix_comic_pages_island_id", table_name="comic_pages")
    op.drop_table("comic_pages")
