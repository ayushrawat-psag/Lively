from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.comics import ComicCatalogResponse
from app.services.comic_service import ComicService

router = APIRouter(tags=["comics"])


@router.get(
    "/comic",
    response_model=ComicCatalogResponse,
    response_model_by_alias=True,
)
def get_comic_catalog(
    island_id: int | None = Query(default=None, alias="islandId"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComicCatalogResponse:
    return ComicService(db).get_catalog(current_user=current_user, island_id=island_id)
