"""add comic_number to islands

Revision ID: 014_add_island_comic_number
Revises: 013_create_comic_pages
Create Date: 2026-07-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_add_island_comic_number"
down_revision: Union[str, None] = "013_create_comic_pages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE islands_comic_number_seq START WITH 0 INCREMENT BY 1 MINVALUE 0")
    op.add_column(
        "islands",
        sa.Column(
            "comic_number",
            sa.Integer(),
            nullable=True,
        ),
    )

    # Whirlpool is always public islandId 0
    op.execute(
        """
        UPDATE islands
        SET comic_number = 0
        WHERE lower(island_name) = 'whirlpool'
        """
    )

    # Remaining islands get deterministic increasing numbers starting at 1
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    ORDER BY display_order ASC, created_at ASC, id ASC
                ) AS rn
            FROM islands
            WHERE comic_number IS NULL
        )
        UPDATE islands AS i
        SET comic_number = ranked.rn
        FROM ranked
        WHERE i.id = ranked.id
        """
    )

    # If Whirlpool was absent, shift numbering so the lowest existing island is 0
    op.execute(
        """
        WITH bounds AS (
            SELECT COALESCE(MIN(comic_number), 0) AS min_number
            FROM islands
        )
        UPDATE islands
        SET comic_number = comic_number - (SELECT min_number FROM bounds)
        WHERE (SELECT COUNT(*) FROM islands WHERE comic_number = 0) = 0
          AND EXISTS (SELECT 1 FROM islands)
        """
    )

    op.alter_column("islands", "comic_number", nullable=False)
    op.create_unique_constraint("uq_islands_comic_number", "islands", ["comic_number"])
    op.create_check_constraint(
        "ck_islands_comic_number_nonneg",
        "islands",
        "comic_number >= 0",
    )

    # Future inserts allocate the next free comic_number via the sequence
    op.execute(
        """
        SELECT setval(
            'islands_comic_number_seq',
            COALESCE((SELECT MAX(comic_number) FROM islands), -1) + 1,
            false
        )
        """
    )
    op.alter_column(
        "islands",
        "comic_number",
        server_default=sa.text("nextval('islands_comic_number_seq')"),
    )


def downgrade() -> None:
    op.alter_column("islands", "comic_number", server_default=None)
    op.drop_constraint("ck_islands_comic_number_nonneg", "islands", type_="check")
    op.drop_constraint("uq_islands_comic_number", "islands", type_="unique")
    op.drop_column("islands", "comic_number")
    op.execute("DROP SEQUENCE IF EXISTS islands_comic_number_seq")
