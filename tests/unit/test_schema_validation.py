"""API 입력값 검증 단위 테스트입니다."""

import pytest
from pydantic import ValidationError

from app.schemas.agent import AgentChatRequest


def test_agent_request_accepts_supported_mobility_type() -> None:
    """지원하는 이동 유형을 정상적으로 허용하는지 검증합니다."""
    request = AgentChatRequest(message="정보문화관 화장실", mobility_type="wheelchair")
    assert request.mobility_type == "wheelchair"


def test_agent_request_rejects_empty_message() -> None:
    """빈 질문을 API 경계에서 차단하는지 검증합니다."""
    with pytest.raises(ValidationError):
        AgentChatRequest(message="")


def test_agent_request_rejects_unknown_fields() -> None:
    """예상하지 않은 요청 필드를 차단하는지 검증합니다."""
    with pytest.raises(ValidationError):
        AgentChatRequest(message="화장실", unexpected="value")
