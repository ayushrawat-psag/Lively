from fastapi import APIRouter

from app.api.v1.endpoints import auth, children, comics, plans, promo_codes

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(plans.router)
api_router.include_router(promo_codes.router)
api_router.include_router(children.router)
api_router.include_router(comics.router)
