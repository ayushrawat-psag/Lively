from uuid import UUID

from pydantic import BaseModel, Field


class ComicPagePublic(BaseModel):
    id: UUID
    image_url: str = Field(..., alias="imageUrl")
    order: int

    model_config = {"populate_by_name": True}


class ComicIslandPublic(BaseModel):
    island_id: int = Field(..., alias="islandId")
    island_name: str = Field(..., alias="islandName")
    total_pages: int = Field(..., alias="totalPages")
    images_per_page: int = Field(..., alias="imagesPerPage")
    pages: list[ComicPagePublic]

    model_config = {"populate_by_name": True}


class ComicCatalogResponse(BaseModel):
    success: bool
    islands: list[ComicIslandPublic]

    model_config = {"populate_by_name": True}
