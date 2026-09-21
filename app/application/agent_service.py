"""접근성 Agent의 핵심 유스케이스를 담당합니다."""

from app.application.intent_service import IntentService
from app.domain.accessibility import AccessibilityFacility
from app.domain.route import RouteOption
from app.schemas.agent import (
    AgentChatResponse,
    FacilityItem,
    RouteFeaturesItem,
    RouteItem,
    RoutePointItem,
)
from app.tools.accessibility_tool import AccessibilitySearchTool
from app.tools.route_tool import RouteSearchTool


class AgentService:
    """질문 분석부터 Tool 호출과 안전한 응답 생성까지 오케스트레이션합니다."""

    def __init__(
        self,
        search_tool: AccessibilitySearchTool,
        intent_service: IntentService,
        route_tool: RouteSearchTool | None = None,
    ) -> None:
        """Agent가 사용할 Tool과 의도 분석 서비스를 주입받습니다."""
        self._search_tool = search_tool
        self._intent_service = intent_service
        self._route_tool = route_tool

    async def chat(
        self,
        message: str,
        mobility_type: str,
        current_latitude: float | None = None,
        current_longitude: float | None = None,
    ) -> AgentChatResponse:
        """사용자 질문을 처리하고 검증된 시설 또는 경로 데이터만 반환합니다."""
        intent = self._intent_service.detect_intent(message)
        if intent is None:
            return AgentChatResponse(
                intent="UNKNOWN",
                items=[],
                routes=[],
                answer=(
                    "찾으시는 시설이나 경로를 조금 더 구체적으로 말씀해 주세요.\n\n"
                    "예: 정보문화관 장애인 화장실, 본관 엘리베이터, "
                    "본관에서 정보문화관까지 휠체어로 가는 길"
                ),
            )

        if intent == "ROUTE":
            return await self._chat_route(
                message,
                mobility_type,
                current_latitude,
                current_longitude,
            )

        buildings = self._intent_service.extract_buildings(message)
        keyword = (
            self._intent_service.extract_photo_keyword(message)
            if intent == "PHOTO"
            else None
        )
        facilities = await self._search_tool.execute(intent, buildings, keyword)
        return AgentChatResponse(
            intent=intent,
            items=[self._to_item(facility) for facility in facilities],
            routes=[],
            answer=self._build_answer(intent, facilities, mobility_type),
        )

    async def _chat_route(
        self,
        message: str,
        mobility_type: str,
        current_latitude: float | None,
        current_longitude: float | None,
    ) -> AgentChatResponse:
        """경로 질문을 Route Tool로 전달하고 안전한 응답을 구성합니다."""
        start_name, destination_name = self._intent_service.extract_route_endpoints(
            message
        )
        if not destination_name:
            return AgentChatResponse(
                intent="ROUTE",
                items=[],
                routes=[],
                answer=(
                    "출발지와 목적지를 확인할 수 없습니다. "
                    "예: 본관에서 정보문화관까지 가는 길을 알려줘"
                ),
            )

        if start_name == "현재위치" and (
            current_latitude is None or current_longitude is None
        ):
            return AgentChatResponse(
                intent="ROUTE",
                items=[],
                routes=[],
                answer=(
                    f"현재 위치에서 {destination_name}까지 경로를 찾으려면 "
                    "현재 위치의 위도와 경도가 필요합니다."
                ),
            )

        if self._route_tool is None:
            return AgentChatResponse(
                intent="ROUTE",
                items=[],
                routes=[],
                answer="경로 조회 기능이 아직 연결되지 않았습니다.",
            )

        routes = await self._route_tool.execute(
            start_name=start_name or "현재위치",
            destination_name=destination_name,
            mobility_type=mobility_type,
            start_latitude=current_latitude if start_name == "현재위치" else None,
            start_longitude=current_longitude if start_name == "현재위치" else None,
        )
        return AgentChatResponse(
            intent="ROUTE",
            items=[],
            routes=[self._to_route_item(route) for route in routes],
            answer=self._build_route_answer(
                destination_name,
                mobility_type,
                routes,
            ),
        )

    def _build_answer(
        self,
        intent: str,
        facilities: list[AccessibilityFacility],
        mobility_type: str,
    ) -> str:
        """조회 결과를 사용자에게 보여줄 안전한 자연어 응답으로 변환합니다."""
        labels = {
            "PHOTO": "사진",
            "TOILET": "장애인 화장실",
            "ELEVATOR": "엘리베이터",
            "RAMP": "경사로",
            "STAIR": "계단",
        }
        label = labels.get(intent, "시설")

        if not facilities:
            return (
                f"등록된 데이터에서 요청하신 {label} 정보를 찾지 못했습니다.\n\n"
                "확인되지 않은 위치나 사진을 임의로 만들어 보여드리지 않습니다."
            )

        if intent == "PHOTO":
            return f"등록된 {label} {len(facilities)}장을 찾았습니다. 아래에서 확인해 주세요."

        lines = [f"등록된 {label} {len(facilities)}곳을 찾았습니다.", ""]
        for index, facility in enumerate(facilities, start=1):
            lines.append(f"{index}. {facility.name}")
            location = facility.floor or "층 정보 없음"
            if facility.description:
                location += f" / {facility.description}"
            lines.append(f"- 위치: {location}")
            lines.append(
                f"- 휠체어 접근 상태: "
                f"{self._accessibility_label(facility.wheelchair_access_status)}"
            )
            lines.append("")

        if mobility_type == "wheelchair":
            lines.append("휠체어 이동 안내: 확인되지 않은 접근 상태는 현장 확인이 필요합니다.")
        else:
            lines.append("필요하면 휠체어 모드로 전환해 접근성 상태를 함께 확인할 수 있습니다.")
        return "\n".join(lines).strip()

    @staticmethod
    def _build_route_answer(
        destination_name: str,
        mobility_type: str,
        routes: list[RouteOption],
    ) -> str:
        """경로 조회 결과를 검증된 수치 중심의 자연어로 변환합니다."""
        if not routes:
            return (
                f"{destination_name}까지 {mobility_type} 이동에 사용할 수 있는 "
                "등록된 경로를 찾지 못했습니다. 정확하지 않은 경로를 만들어 안내하지 않습니다."
            )

        first = routes[0]
        danger_text = (
            f"위험 지점 {first.danger_count}곳이 감지되었습니다."
            if first.danger_count
            else "응답에 포함된 위험 지점은 없습니다."
        )
        return (
            f"{destination_name}까지 {len(routes)}개의 경로를 확인했습니다. "
            f"첫 번째 경로는 약 {first.distance:.0f}m, "
            f"예상 {first.duration:.0f}분입니다. {danger_text}"
        )

    @staticmethod
    def _accessibility_label(status: str) -> str:
        """접근성 상태 코드를 사용자용 문구로 변환합니다."""
        labels = {
            "ACCESSIBLE": "접근 가능 확인",
            "NOT_ACCESSIBLE": "접근 어려움",
            "UNKNOWN": "현장 확인 필요",
        }
        return labels.get(status, "현장 확인 필요")

    @staticmethod
    def _to_item(facility: AccessibilityFacility) -> FacilityItem:
        """도메인 모델을 API 응답 스키마로 변환합니다."""
        return FacilityItem(
            id=facility.id,
            name=facility.name,
            type=facility.type,
            floor=facility.floor,
            description=facility.description,
            wheelchair_access_status=facility.wheelchair_access_status,
            latitude=facility.latitude,
            longitude=facility.longitude,
            photo_url=facility.photo_url,
        )

    @staticmethod
    def _to_route_item(route: RouteOption) -> RouteItem:
        """경로 도메인 모델을 API 응답 스키마로 변환합니다."""
        return RouteItem(
            id=route.id,
            title=route.title,
            distance=route.distance,
            duration=route.duration,
            danger_count=route.danger_count,
            features=RouteFeaturesItem(
                stairs=route.features.stairs,
                ramps=route.features.ramps,
                elevators=route.features.elevators,
                crosswalks=route.features.crosswalks,
            ),
            path=[
                RoutePointItem(
                    id=point.id,
                    name=point.name,
                    latitude=point.latitude,
                    longitude=point.longitude,
                    type=point.type,
                )
                for point in route.path
            ],
        )
