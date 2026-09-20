"""Agent 채팅 HTTP 엔드포인트입니다."""

from fastapi import APIRouter, Depends

from app.application.agent_service import AgentService
from app.application.intent_service import IntentService
from app.core.config import get_settings
from app.domain.ports import AccessibilityRepository
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
        # Pydantic의 max_length와 설정값이 서로 다른 환경에서도 방어적으로 제한합니다.
        raise ValueError("질문 길이가 허용 범위를 초과했습니다.")
    return await service.chat(request.message, request.mobility_type)
