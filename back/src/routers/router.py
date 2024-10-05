from fastapi import APIRouter
from routers import keiba
router = APIRouter()

router.include_router(keiba.router, prefix="/keiba")
