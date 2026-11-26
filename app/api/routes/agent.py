"""Agent 채팅 HTTP 엔드포인트입니다."""

import json
import logging
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_agent_service
from app.application.agent_service import AgentService
from app.core.config import get_settings
from app.schemas.agent import AgentChatRequest, AgentChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


def _validate_message_length(message: str) -> None:
    """질문 길이 제한을 검사하고 초과하면 422를 발생시킵니다."""
    settings = get_settings()
    if len(message) > settings.max_agent_message_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"질문은 {settings.max_agent_message_length}자 이내여야 합니다.",
        )


def _sse(event: str, data: dict[str, Any]) -> str:
    """SSE 프로토콜 형식(event/data 두 줄 + 빈 줄)의 문자열을 만듭니다."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat", response_model=AgentChatResponse)
async def chat(
    request: AgentChatRequest,
    service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentChatResponse:
    """자연어 질문을 Agent 서비스로 전달하고 구조화된 결과를 반환합니다."""
    _validate_message_length(request.message)
    return await service.chat(
        message=request.message,
        mobility_type=request.mobility_type,
        current_latitude=request.current_latitude,
        current_longitude=request.current_longitude,
    )


@router.post("/chat/stream")
async def chat_stream(
    request: AgentChatRequest,
    service: Annotated[AgentService, Depends(get_agent_service)],
) -> StreamingResponse:
    """처리 단계(step)와 최종 응답(result)을 SSE로 실시간 전달합니다."""
    _validate_message_length(request.message)

    async def event_source() -> AsyncIterator[str]:
        """서비스 이벤트를 SSE 문자열로 변환하고, 실패하면 error 이벤트로 알립니다."""
        try:
            async for item in service.chat_stream(
                message=request.message,
                mobility_type=request.mobility_type,
                current_latitude=request.current_latitude,
                current_longitude=request.current_longitude,
            ):
                yield _sse(item["event"], item["data"])
        except Exception:
            logger.exception("Agent 스트리밍 처리 중 오류가 발생했습니다.")
            yield _sse(
                "error", {"message": "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요."}
            )

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx 등 프록시가 응답을 모아서 보내지 않도록 함
        },
    )
