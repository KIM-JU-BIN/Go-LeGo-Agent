"""API 입력값 검증 단위 테스트입니다."""

"""Tests for Agent request schema validation."""

import pytest
from pydantic import ValidationError

from app.schemas.agent import AgentChatRequest


def test_agent_request_accepts_camel_case_mobility_type() -> None:
    """camelCase mobilityType 입력을 허용하는지 검증합니다."""
    request = AgentChatRequest(
        message="휠체어로 갈 수 있는 길 알려줘",
        mobilityType="wheelchair",
    )

    assert request.mobility_type == "wheelchair"


def test_agent_request_accepts_current_location() -> None:
    """현재 위치 좌표를 route 질문에 사용할 수 있는지 검증합니다."""
    request = AgentChatRequest(
        message="지금 여기서 정보문화관까지 가는 길 알려줘",
        currentLatitude=37.5600,
        currentLongitude=127.0130,
    )

    assert request.current_latitude == 37.5600
    assert request.current_longitude == 127.0130


def test_agent_request_rejects_empty_message() -> None:
    """빈 메시지를 허용하지 않는지 검증합니다."""
    with pytest.raises(ValidationError):
        AgentChatRequest(message="")


def test_agent_request_rejects_unknown_fields() -> None:
    """정의되지 않은 필드를 허용하지 않는지 검증합니다."""
    with pytest.raises(ValidationError):
        AgentChatRequest(
            message="정보문화관 알려줘",
            unknown_field="invalid",
        )
