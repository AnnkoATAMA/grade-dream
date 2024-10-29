from fastapi import APIRouter
from routers import keiba, line
router = APIRouter()

router.include_router(keiba.keiba_router, prefix="/keiba")
router.include_router(line.line_router, prefix="/line")