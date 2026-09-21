"""Agent 애플리케이션 서비스 단위 테스트입니다."""

import pytest

from app.application.agent_service import AgentService
from app.application.intent_service import IntentService
from app.domain.accessibility import AccessibilityFacility
from app.domain.ports import AccessibilityRepository
from app.domain.route import RouteFeatures, RouteOption, RoutePoint
from app.domain.route_ports import RouteRepository
from app.tools.accessibility_tool import AccessibilitySearchTool
from app.tools.route_tool import RouteSearchTool


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


class FakeRouteRepository(RouteRepository):
    """외부 Go-LeGo API 없이 경로 Agent 흐름을 검증하는 메모리 저장소입니다."""

    async def find_routes(
        self,
        start_name: str,
        destination_name: str,
        mobility_type: str,
        start_latitude: float | None = None,
        start_longitude: float | None = None,
        destination_latitude: float | None = None,
        destination_longitude: float | None = None,
    ) -> list[RouteOption]:
        """테스트용 접근성 경로를 반환합니다."""
        return [
            RouteOption(
                id="accessible",
                title="추천 경로",
                distance=420.0,
                duration=7.0,
                danger_count=0,
                features=RouteFeatures(stairs=0, ramps=1, elevators=1, crosswalks=2),
                path=(
                    RoutePoint(
                        id="start",
                        name=start_name,
                        latitude=37.0,
                        longitude=127.0,
                        type="entrance",
                    ),
                    RoutePoint(
                        id="end",
                        name=destination_name,
                        latitude=37.001,
                        longitude=127.001,
                        type="entrance",
                    ),
                ),
            )
        ]


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


@pytest.mark.asyncio
async def test_agent_returns_verified_route() -> None:
    """Route Tool의 검증된 경로가 Agent 응답으로 변환되는지 검증합니다."""
    accessibility_tool = AccessibilitySearchTool(FakeAccessibilityRepository())
    route_tool = RouteSearchTool(FakeRouteRepository())
    service = AgentService(
        accessibility_tool,
        IntentService(),
        route_tool=route_tool,
    )

    response = await service.chat(
        "본관에서 정보문화관까지 휠체어로 가는 길",
        "wheelchair",
    )

    assert response.intent == "ROUTE"
    assert response.items == []
    assert len(response.routes) == 1
    assert response.routes[0].distance == 420.0
    assert response.routes[0].features.ramps == 1
    assert "420m" in response.answer
