from fastapi import APIRouter
from src.api.v1.endpoints import auth, pals, breeding

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(pals.router, prefix="/pals", tags=["Pal Inventory"])
api_router.include_router(breeding.router, prefix="/breeding", tags=["Breeding Inventory"])