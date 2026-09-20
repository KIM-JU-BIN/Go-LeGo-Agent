"""Agent 채팅 HTTP 엔드포인트입니다."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.agent_service import AgentService
from app.application.intent_service import IntentService
from app.core.config import get_settings
from app.infrastructure.accessibility_repository import MySQLAccessibilityRepository
from app.schemas.agent import AgentChatRequest, AgentChatResponse

router = APIRouter(prefix="/agent", tags=["agent"])


_repository = MySQLAccessibilityRepository()
_intent_service = IntentService()


def get_agent_service() -> AgentService:
    """HTTP 라우터가 사용할 AgentService 의존성을 생성합니다."""
    return AgentService(repository=_repository, intent_service=_intent_service)


@router.post("/chat", response_model=AgentChatResponse)
async def chat(request: AgentChatRequest, service: AgentService = Depends(get_agent_service)) -> AgentChatResponse:
    """자연어 질문을 Agent 서비스로 전달하고 구조화된 결과를 반환합니다."""
    settings = get_settings()
    if len(request.message) > settings.max_agent_message_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"질문은 {settings.max_agent_message_length}자 이내여야 합니다.",
        )
    return await service.chat(request.message, request.mobility_type)
