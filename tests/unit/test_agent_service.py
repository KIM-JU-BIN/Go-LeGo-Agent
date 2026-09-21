"""Agent 애플리케이션 서비스 단위 테스트입니다."""

import pytest

from app.application.agent_service import AgentService
from app.application.intent_service import IntentService
from app.domain.accessibility import AccessibilityFacility
from app.domain.ports import AccessibilityRepository
from app.tools.accessibility_tool import AccessibilitySearchTool


class FakeAccessibilityRepository(AccessibilityRepository):
    """DB 없이 Agent 응답 로직을 검증하기 위한 메모리 저장소입니다."""

    async def search_facilities(
        self,
        intent: str,
        building_names: list[str],
    ) -> list[AccessibilityFacility]:
        """테스트용 시설 데이터를 반환합니다."""
        return (
            [
                AccessibilityFacility(
                    id="a1000000-0000-4000-8000-000000000001",
                    name="정보문화관 장애인 화장실",
                    type="accessible_toilet",
                    floor="1층",
                    description="동측 복도",
                    wheelchair_access_status="UNKNOWN",
                    latitude=37.0,
                    longitude=127.0,
                )
            ]
            if intent == "TOILET"
            else []
        )


@pytest.mark.asyncio
async def test_agent_does_not_fabricate_unknown_question() -> None:
    """지원하지 않는 질문에 임의의 시설을 만들어 답하지 않는지 검증합니다."""
    tool = AccessibilitySearchTool(FakeAccessibilityRepository())
    service = AgentService(tool, IntentService())
    response = await service.chat("오늘 날씨 알려줘", "walking")
    assert response.intent == "UNKNOWN"
    assert response.items == []


@pytest.mark.asyncio
async def test_agent_returns_verified_domain_items() -> None:
    """저장소의 시설 데이터가 Tool을 거쳐 API 응답으로 변환되는지 검증합니다."""
    tool = AccessibilitySearchTool(FakeAccessibilityRepository())
    service = AgentService(tool, IntentService())
    response = await service.chat(
        "정보문화관 장애인 화장실 어디 있어?",
        "wheelchair",
    )
    assert response.intent == "TOILET"
    assert len(response.items) == 1
    assert response.items[0].wheelchair_access_status == "UNKNOWN"
    assert "현장 확인" in response.answer or "확인 필요" in response.answer
