"""add images_per_page to islands

Revision ID: 015_add_island_images_per_page
Revises: 014_add_island_comic_number
Create Date: 2026-07-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015_add_island_images_per_page"
down_revision: Union[str, None] = "014_add_island_comic_number"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "islands",
        sa.Column(
            "images_per_page",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.create_check_constraint(
        "ck_islands_images_per_page_positive",
        "islands",
        "images_per_page > 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_islands_images_per_page_positive", "islands", type_="check")
    op.drop_column("islands", "images_per_page")
