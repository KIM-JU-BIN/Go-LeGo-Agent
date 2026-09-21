"""FastAPI 애플리케이션 진입점입니다."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.agent import router as agent_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.database import close_database, initialize_database

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 필요한 공용 자원을 관리합니다."""
    settings = get_settings()
    if settings.database_enabled:
        await initialize_database()
    yield
    if settings.database_enabled:
        await close_database()


app = FastAPI(
    title="Go-LeGo Accessibility Agent",
    version="2.0.0",
    description="Go-LeGo 프로젝트에 이식할 수 있도록 계층형으로 구성한 접근성 Agent API입니다.",
    lifespan=lifespan,
)

app.mount("/css", StaticFiles(directory=PUBLIC_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=PUBLIC_DIR / "js"), name="js")

app.include_router(health_router, prefix="/api")
app.include_router(agent_router, prefix="/api")


@app.get("/", tags=["system"], include_in_schema=False)
async def root() -> FileResponse:
    """교수님 시연용 접근성 Agent 챗봇 화면을 반환합니다."""
    return FileResponse(PUBLIC_DIR / "index.html")
