"""Agent 애플리케이션 서비스 단위 테스트입니다."""

import pytest

from app.application.agent_service import AgentService
from app.application.intent_service import IntentService
from app.domain.accessibility import AccessibilityFacility
from app.domain.ports import AccessibilityRepository
from app.domain.route import RouteFeatures, RouteOption, RoutePoint
from app.domain.route_ports import RouteRepository
from app.schemas.agent import AgentIntent
from app.tools.accessibility_tool import AccessibilitySearchTool
from app.tools.route_tool import RouteSearchTool
from app.tools.place_search_tool import PlaceCandidate


class FakeAccessibilityRepository(AccessibilityRepository):
    """DB 없이 Agent 응답 로직을 검증하기 위한 메모리 저장소입니다."""

    async def search_facilities(
        self,
        intent: str,
        building_names: list[str],
        keyword: str | None = None,
    ) -> list[AccessibilityFacility]:
        """테스트용 시설과 사진 데이터를 반환합니다."""
        if intent == "PHOTO":
            return [
                AccessibilityFacility(
                    id="photo-1",
                    name="정보문화관 정문",
                    type="entrance",
                    floor="1층",
                    description="정문 외부",
                    wheelchair_access_status="UNKNOWN",
                    latitude=37.0,
                    longitude=127.0,
                    photo_url="http://127.0.0.1:3000/panoramas/front.jpg",
                )
            ]

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


class FakeLLMIntentProvider:
    """실제 OpenAI API 없이 LLM 결과를 주입해 Agent 연동을 검증합니다."""

    def __init__(self, result: AgentIntent) -> None:
        """테스트에서 반환할 구조화된 Intent를 저장합니다."""
        self._result = result

    async def classify(
        self,
        message: str,
        mobility_type: str,
    ) -> AgentIntent:
        """고정된 Intent를 반환해 LLM Tool Selection 흐름을 검증합니다."""
        return self._result


class FakePlaceSearchTool:
    """실제 Kakao API 없이 외부 장소 검색 흐름을 검증합니다."""

    enabled = True

    def __init__(self, results: dict[str, list[PlaceCandidate]]) -> None:
        self._results = results
        self.queries: list[str] = []

    async def execute(self, query: str, size: int = 5) -> list[PlaceCandidate]:
        self.queries.append(query)
        return self._results.get(query, [])


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
    assert "\\n" not in response.answer


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


@pytest.mark.asyncio
async def test_agent_returns_photo_result() -> None:
    """사진 질문이 등록된 POI 사진 URL을 반환하는지 검증합니다."""
    tool = AccessibilitySearchTool(FakeAccessibilityRepository())
    service = AgentService(tool, IntentService())
    response = await service.chat("정보문화관 정문 사진 보여줘", "walking")
    assert response.intent == "PHOTO"
    assert response.items[0].photo_url.endswith("/panoramas/front.jpg")


@pytest.mark.asyncio
async def test_agent_uses_structured_llm_intent_before_rule_fallback() -> None:
    """LLM이 구조화한 Intent와 장소를 기존 Tool 실행에 연결하는지 검증합니다."""
    accessibility_tool = AccessibilitySearchTool(FakeAccessibilityRepository())
    route_tool = RouteSearchTool(FakeRouteRepository())
    llm_provider = FakeLLMIntentProvider(
        AgentIntent(
            intent="ROUTE",
            building_names=["본관", "정보문화관"],
            start_name="본관",
            destination_name="정보문화관",
            photo_keyword=None,
        )
    )
    service = AgentService(
        accessibility_tool,
        IntentService(),
        route_tool=route_tool,
        llm_intent_service=llm_provider,
    )

    response = await service.chat("정보문화관으로 안내 부탁해", "wheelchair")

    assert response.intent == "ROUTE"
    assert len(response.routes) == 1
    assert response.routes[0].path[0].name == "본관"
    assert response.routes[0].path[1].name == "정보문화관"


@pytest.mark.asyncio
async def test_external_route_keeps_explicit_origin_and_resolves_place() -> None:
    """LLM이 추출한 외부 출발지를 현재 위치로 덮어쓰지 않고 장소 검색에 전달합니다."""
    accessibility_tool = AccessibilitySearchTool(FakeAccessibilityRepository())
    route_tool = RouteSearchTool(FakeRouteRepository())
    place_tool = FakePlaceSearchTool({
        "한양대역": [
            PlaceCandidate(
                name="한양대역",
                address="서울 성동구",
                road_address="서울 성동구 왕십리로",
                latitude=37.555,
                longitude=127.043,
                place_url="https://place.example",
            )
        ]
    })
    llm_provider = FakeLLMIntentProvider(
        AgentIntent(
            intent="ROUTE",
            building_names=["정보문화관"],
            start_name="한양대역",
            destination_name="정보문화관",
            photo_keyword=None,
        )
    )
    service = AgentService(
        accessibility_tool,
        IntentService(),
        route_tool=route_tool,
        llm_intent_service=llm_provider,
        place_search_tool=place_tool,
    )

    response = await service.chat(
        "한양대역에서 정보문화관까지 안내해줘",
        "wheelchair",
        current_latitude=37.56,
        current_longitude=127.04,
    )

    assert place_tool.queries == ["한양대역"]
    assert response.intent == "ROUTE"
    assert response.routes == []
    assert "출발지: 한양대역" in response.answer
    assert "외부 장소 확인 단계" in response.answer


@pytest.mark.asyncio
async def test_external_place_search_asks_when_results_are_ambiguous() -> None:
    """검색 결과가 모호하면 임의 선택하지 않고 사용자에게 장소를 확인합니다."""
    place_tool = FakePlaceSearchTool({
        "한양대": [
            PlaceCandidate("한양대학교", "서울", "", 37.55, 127.04),
            PlaceCandidate("한양대학교 ERICA", "안산", "", 37.30, 126.83),
        ]
    })
    llm_provider = FakeLLMIntentProvider(
        AgentIntent(
            intent="ROUTE",
            building_names=["정보문화관"],
            start_name="한양대",
            destination_name="정보문화관",
            photo_keyword=None,
        )
    )
    service = AgentService(
        AccessibilitySearchTool(FakeAccessibilityRepository()),
        IntentService(),
        route_tool=RouteSearchTool(FakeRouteRepository()),
        llm_intent_service=llm_provider,
        place_search_tool=place_tool,
    )

    response = await service.chat("한양대에서 정보문화관까지", "walking")

    assert response.routes == []
    assert "여러 개" in response.answer
    assert "1. 한양대학교" in response.answer
    assert "2. 한양대학교 ERICA" in response.answer
