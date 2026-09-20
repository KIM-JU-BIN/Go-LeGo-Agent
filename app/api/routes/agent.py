"""Agent 채팅 HTTP 엔드포인트입니다."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_agent_service
from app.application.agent_service import AgentService
from app.core.config import get_settings
from app.schemas.agent import AgentChatRequest, AgentChatResponse

router = APIRouter(prefix="/agent", tags=["agent"])


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
