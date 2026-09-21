"""서비스와 데이터베이스 상태를 확인하는 health API입니다."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.database import ping_database

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """애플리케이션과 MySQL 연결 상태를 확인합니다."""
    settings = get_settings()
    if not settings.database_enabled:
        return {"ok": True, "database": None, "database_enabled": False}

    try:
        database = await ping_database()
        return {"ok": True, "database": database, "connected": True}
    except Exception as exc:
        return {
            "ok": False,
            "database": None,
            "connected": False,
            "detail": str(exc),
        }
