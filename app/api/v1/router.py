from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    children,
    comics,
    fridge_inventory,
    habit_tracker,
    plans,
    promo_codes,
    whirlpool_island,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(plans.router)
api_router.include_router(promo_codes.router)
api_router.include_router(children.router)
api_router.include_router(whirlpool_island.router)
api_router.include_router(habit_tracker.router)
api_router.include_router(fridge_inventory.router)
api_router.include_router(comics.router)
