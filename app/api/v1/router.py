from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.image import router as image_router
from app.api.v1.payments import router as payments_router

# Create the main API router
api_router = APIRouter()

# Include all the routers from different modules
api_router.include_router(auth_router)
api_router.include_router(image_router)
api_router.include_router(payments_router) 