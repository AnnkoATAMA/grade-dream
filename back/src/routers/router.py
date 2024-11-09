from fastapi import APIRouter
from routers import keiba, line, race_calendar
router = APIRouter()

router.include_router(keiba.keiba_router, prefix="/keiba")
router.include_router(line.line_router, prefix="/line")
router.include_router(race_calendar.calendar_router, prefix="/calendar")