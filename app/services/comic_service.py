from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.comic_page import ComicPage
from app.models.enums import UserType
from app.models.island import Island
from app.models.user import User
from app.repositories.comic_repository import ComicRepository
from app.schemas.comics import ComicCatalogResponse, ComicIslandPublic, ComicPagePublic


class ComicService:
    def __init__(self, db: Session) -> None:
        self.repo = ComicRepository(db)

    @staticmethod
    def _authorize_child(current_user: User) -> None:
        if current_user.user_type != UserType.CHILD or not current_user.is_child:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"success": False, "message": "Forbidden"},
            )

    @staticmethod
    def _island_to_public(island: Island, pages: list[ComicPage]) -> ComicIslandPublic:
        public_pages = [
            ComicPagePublic(id=page.id, imageUrl=page.image_url, order=page.display_order)
            for page in pages
        ]
        return ComicIslandPublic(
            islandId=island.comic_number,
            islandName=island.island_name,
            totalPages=len(public_pages),
            imagesPerPage=island.images_per_page,
            pages=public_pages,
        )

    def get_catalog(
        self,
        *,
        current_user: User,
        island_id: int | None = None,
    ) -> ComicCatalogResponse:
        self._authorize_child(current_user)

        if island_id is not None:
            if island_id < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"success": False, "message": "Invalid island id"},
                )
            islands = self.repo.list_active_islands_with_pages(comic_number=island_id)
            if not islands:
                island = self.repo.get_active_island_by_comic_number(island_id)
                if not island:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail={"success": False, "message": "Island not found"},
                    )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"success": False, "message": "Comic not found"},
                )
            return ComicCatalogResponse(
                success=True,
                islands=[
                    self._island_to_public(island, pages) for island, pages in islands
                ],
            )

        islands = self.repo.list_active_islands_with_pages()
        return ComicCatalogResponse(
            success=True,
            islands=[
                self._island_to_public(island, pages) for island, pages in islands
            ],
        )
