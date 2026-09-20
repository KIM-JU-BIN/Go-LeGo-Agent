"""FastAPI 애플리케이션 진입점입니다."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.agent import router as agent_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.database import close_database, initialize_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 필요한 공용 자원을 관리합니다."""
    settings = get_settings()
    if settings.database_enabled:
        await initialize_database()
    yield
    if settings.database_enabled:
        await close_database()


# FastAPI 애플리케이션 인스턴스를 생성합니다.
app = FastAPI(
    title="Go-LeGo Accessibility Agent",
    version="2.0.0",
    description="Go-LeGo 프로젝트에 이식할 수 있도록 계층형으로 구성한 접근성 Agent API입니다.",
    lifespan=lifespan,
)

app.include_router(health_router, prefix="/api")
app.include_router(agent_router, prefix="/api")


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    """Agent 서버가 정상적으로 실행 중인지 확인하는 기본 엔드포인트입니다."""
    return {"service": "go-lego-agent", "status": "running"}
