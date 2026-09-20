"""MySQL 연결 풀을 관리하는 인프라 모듈입니다."""

from typing import Any

import aiomysql

from app.core.config import get_settings


_pool: aiomysql.Pool | None = None


async def initialize_database() -> None:
    """애플리케이션 시작 시 비동기 MySQL 연결 풀을 생성합니다."""
    global _pool
    if _pool is not None:
        return

    settings = get_settings()
    _pool = await aiomysql.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        db=settings.db_name,
        minsize=settings.db_pool_min_size,
        maxsize=settings.db_pool_max_size,
        autocommit=True,
        charset="utf8mb4",
    )


async def close_database() -> None:
    """애플리케이션 종료 시 MySQL 연결 풀을 안전하게 닫습니다."""
    global _pool
    if _pool is None:
        return
    _pool.close()
    await _pool.wait_closed()
    _pool = None


async def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    """SQL 조회 결과를 딕셔너리 목록으로 반환합니다."""
    if _pool is None:
        await initialize_database()
    assert _pool is not None

    async with _pool.acquire() as connection:
        async with connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(query, params)
            rows = await cursor.fetchall()
            return list(rows)


async def ping_database() -> str:
    """현재 연결된 데이터베이스 이름을 조회해 연결 상태를 검증합니다."""
    rows = await fetch_all("SELECT DATABASE() AS database_name")
    return str(rows[0]["database_name"]) if rows else ""
