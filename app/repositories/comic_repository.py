from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.comic_page import ComicPage
from app.models.enums import ContentStatus
from app.models.island import Island


class ComicRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_active_islands_with_pages(
        self,
        *,
        comic_number: int | None = None,
    ) -> list[tuple[Island, list[ComicPage]]]:
        stmt = (
            select(Island)
            .options(selectinload(Island.comic_pages))
            .where(Island.status == ContentStatus.ACTIVE)
            .order_by(Island.comic_number.asc(), Island.id.asc())
        )
        if comic_number is not None:
            stmt = stmt.where(Island.comic_number == comic_number)

        results: list[tuple[Island, list[ComicPage]]] = []
        for island in self.db.scalars(stmt).all():
            active_pages = sorted(
                (
                    page
                    for page in island.comic_pages
                    if page.status == ContentStatus.ACTIVE
                ),
                key=lambda page: (page.display_order, page.id),
            )
            if not active_pages:
                continue
            results.append((island, active_pages))
        return results

    def get_active_island_by_comic_number(self, comic_number: int) -> Island | None:
        stmt = select(Island).where(
            Island.comic_number == comic_number,
            Island.status == ContentStatus.ACTIVE,
        )
        return self.db.scalars(stmt).first()
