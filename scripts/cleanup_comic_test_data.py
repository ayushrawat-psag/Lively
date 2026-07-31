"""Keep only the Whirlpool island and remove leftover comic/island test data."""

from __future__ import annotations

from sqlalchemy import func, select, text

from app.db.session import SessionLocal
from app.models.comic_page import ComicPage
from app.models.habit import Habit
from app.models.island import Island
from app.models.prize_item import PrizeItem
from app.models.simulation import Simulation


def main() -> None:
    db = SessionLocal()
    try:
        keep = db.scalar(
            select(Island).where(
                func.lower(Island.island_name) == "whirlpool",
                Island.comic_number == 0,
            )
        )
        if keep is None:
            raise SystemExit("Whirlpool island (comic_number=0) not found")

        delete_ids = [
            island.id
            for island in db.scalars(select(Island).where(Island.id != keep.id)).all()
        ]
        print(f"keeping={keep.id} {keep.island_name!r} comic_number={keep.comic_number}")
        print(f"deleting_islands={len(delete_ids)}")

        if delete_ids:
            sim_ids = [
                simulation.id
                for simulation in db.scalars(
                    select(Simulation).where(Simulation.island_id.in_(delete_ids))
                ).all()
            ]
            if sim_ids:
                habit_ids = [
                    habit.id
                    for habit in db.scalars(
                        select(Habit).where(Habit.simulation_id.in_(sim_ids))
                    ).all()
                ]
                prize_ids = [
                    prize.id
                    for prize in db.scalars(
                        select(PrizeItem).where(PrizeItem.simulation_id.in_(sim_ids))
                    ).all()
                ]

                if habit_ids:
                    db.execute(
                        text("DELETE FROM habit_tracker WHERE habit_id = ANY(:ids)"),
                        {"ids": habit_ids},
                    )
                    db.execute(
                        text("DELETE FROM user_rewards WHERE habit_id = ANY(:ids)"),
                        {"ids": habit_ids},
                    )
                    db.execute(
                        text("DELETE FROM habits WHERE id = ANY(:ids)"),
                        {"ids": habit_ids},
                    )
                if prize_ids:
                    db.execute(
                        text("DELETE FROM user_rewards WHERE prize_item_id = ANY(:ids)"),
                        {"ids": prize_ids},
                    )
                    db.execute(
                        text("DELETE FROM prize_items WHERE id = ANY(:ids)"),
                        {"ids": prize_ids},
                    )

                db.execute(
                    text("DELETE FROM simulation_answers WHERE simulation_id = ANY(:ids)"),
                    {"ids": sim_ids},
                )
                db.execute(
                    text(
                        """
                        UPDATE user_activity
                        SET last_completed_simulation_id = NULL
                        WHERE last_completed_simulation_id = ANY(:ids)
                        """
                    ),
                    {"ids": sim_ids},
                )
                db.execute(
                    text("DELETE FROM simulations WHERE id = ANY(:ids)"),
                    {"ids": sim_ids},
                )

            db.execute(
                text("DELETE FROM learner_permit_badges WHERE island_id = ANY(:ids)"),
                {"ids": delete_ids},
            )
            db.execute(
                text("DELETE FROM comic_pages WHERE island_id = ANY(:ids)"),
                {"ids": delete_ids},
            )
            db.execute(
                text("DELETE FROM locations WHERE island_id = ANY(:ids)"),
                {"ids": delete_ids},
            )
            db.execute(
                text("DELETE FROM islands WHERE id = ANY(:ids)"),
                {"ids": delete_ids},
            )

        deleted_pages = db.execute(
            text(
                """
                DELETE FROM comic_pages
                WHERE island_id = :island_id
                  AND image_url LIKE 'https://cdn.example.com/%'
                """
            ),
            {"island_id": str(keep.id)},
        ).rowcount
        print(f"deleted_whirlpool_test_pages={deleted_pages}")

        db.execute(text("SELECT setval('islands_comic_number_seq', 1, false)"))
        db.commit()

        islands = list(db.scalars(select(Island).order_by(Island.comic_number)).all())
        print(f"remaining_islands={len(islands)}")
        for island in islands:
            page_count = db.scalar(
                select(func.count())
                .select_from(ComicPage)
                .where(ComicPage.island_id == island.id)
            )
            print(
                f"  comic_number={island.comic_number} "
                f"name={island.island_name!r} pages={page_count}"
            )
        print(
            "remaining_comic_pages=",
            db.scalar(select(func.count()).select_from(ComicPage)),
        )
        print(
            "remaining_simulations=",
            db.scalar(select(func.count()).select_from(Simulation)),
        )
        print("cleanup_ok")
    finally:
        db.close()


if __name__ == "__main__":
    main()
