"""접근성 Agent의 핵심 유스케이스를 담당합니다."""

import re

import httpx

from app.application.intent_service import IntentService
from app.application.llm_intent_service import LLMIntentProvider
from app.domain.accessibility import AccessibilityFacility
from app.domain.route import RouteOption
from app.schemas.agent import (
    AgentChatResponse,
    AgentIntent,
    FacilityItem,
    RouteFeaturesItem,
    RouteItem,
    RoutePointItem,
)
from app.tools.accessibility_tool import AccessibilitySearchTool
from app.tools.place_search_tool import PlaceCandidate, PlaceSearchTool
from app.tools.route_tool import RouteSearchTool


class AgentService:
    """질문 분석부터 Tool 호출과 안전한 응답 생성까지 오케스트레이션합니다."""

    def __init__(
        self,
        search_tool: AccessibilitySearchTool,
        intent_service: IntentService,
        route_tool: RouteSearchTool | None = None,
        llm_intent_service: LLMIntentProvider | None = None,
        place_search_tool: PlaceSearchTool | None = None,
    ) -> None:
        """Agent가 사용할 Tool, 규칙 기반 Intent, 선택적 LLM 분석기를 주입받습니다."""
        self._search_tool = search_tool
        self._intent_service = intent_service
        self._route_tool = route_tool
        self._llm_intent_service = llm_intent_service
        self._place_search_tool = place_search_tool

    async def chat(
        self,
        message: str,
        mobility_type: str,
        current_latitude: float | None = None,
        current_longitude: float | None = None,
    ) -> AgentChatResponse:
        """사용자 질문을 처리하고 검증된 시설 또는 경로 데이터만 반환합니다."""
        llm_intent = await self._classify_with_llm(message, mobility_type)
        intent = (
            llm_intent.intent
            if llm_intent is not None
            else self._intent_service.detect_intent(message)
        )

        if intent is None or intent == "UNKNOWN":
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
                llm_intent,
            )

        buildings = self._resolve_buildings(message, llm_intent)
        keyword = (
            self._resolve_photo_keyword(message, llm_intent)
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

    async def _classify_with_llm(
        self,
        message: str,
        mobility_type: str,
    ) -> AgentIntent | None:
        """설정된 LLM으로 질문을 분석하고, 사용할 수 없으면 규칙 기반 분석으로 넘깁니다."""
        if self._llm_intent_service is None:
            return None
        return await self._llm_intent_service.classify(message, mobility_type)

    def _resolve_buildings(
        self,
        message: str,
        llm_intent: AgentIntent | None,
    ) -> list[str]:
        """LLM이 반환한 건물명을 지원 목록과 대조한 뒤 안전한 후보만 사용합니다."""
        if llm_intent is not None:
            buildings = [
                building
                for building in llm_intent.building_names
                if building in self._intent_service.BUILDINGS
            ]
            if buildings:
                return list(dict.fromkeys(buildings))
        return self._intent_service.extract_buildings(message)

    def _resolve_photo_keyword(
        self,
        message: str,
        llm_intent: AgentIntent | None,
    ) -> str | None:
        """LLM 사진 키워드를 허용 목록과 검증하고 실패하면 규칙 기반 추출을 사용합니다."""
        allowed = {"정문", "후문", "입구", "출입구"}
        if llm_intent is not None and llm_intent.photo_keyword in allowed:
            return llm_intent.photo_keyword
        return self._intent_service.extract_photo_keyword(message)

    async def _chat_route(
        self,
        message: str,
        mobility_type: str,
        current_latitude: float | None,
        current_longitude: float | None,
        llm_intent: AgentIntent | None,
    ) -> AgentChatResponse:
        """경로 질문을 Route Tool로 전달하고 안전한 응답을 구성합니다."""
        fallback_start, fallback_destination = self._intent_service.extract_route_endpoints(
            message
        )
        start_name, destination_name = self._resolve_route_endpoints(
            llm_intent,
            fallback_start,
            fallback_destination,
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

        known_places = set(self._intent_service.BUILDINGS) | {"현재위치"}
        external_names = list(dict.fromkeys(
            name for name in (start_name, destination_name)
            if name and name not in known_places
        ))
        if external_names:
            return await self._resolve_external_route_places(
                start_name=start_name or "현재위치",
                destination_name=destination_name,
                external_names=external_names,
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

    def _resolve_route_endpoints(
        self,
        llm_intent: AgentIntent | None,
        fallback_start: str | None,
        fallback_destination: str | None,
    ) -> tuple[str | None, str | None]:
        """LLM이 추출한 장소명을 보존하고 빈 값만 규칙 기반 결과로 보완합니다."""
        if llm_intent is not None:
            start = self._clean_place_name(llm_intent.start_name) or fallback_start
            destination = (
                self._clean_place_name(llm_intent.destination_name)
                or fallback_destination
            )
            return start, destination
        return fallback_start, fallback_destination

    @staticmethod
    def _clean_place_name(value: str | None) -> str | None:
        """LLM 장소 후보를 길이와 공백 기준으로 검증합니다. 실제 존재 여부는 Place Tool이 확인합니다."""
        if not value:
            return None
        cleaned = " ".join(value.strip().split())
        if not cleaned or len(cleaned) > 100:
            return None
        return cleaned

    async def _resolve_external_route_places(
        self,
        start_name: str,
        destination_name: str,
        external_names: list[str],
    ) -> AgentChatResponse:
        """외부 장소명을 실제 장소 검색 결과로 검증하되 미구현 경로 결합을 가장하지 않습니다."""
        if self._place_search_tool is None:
            return AgentChatResponse(
                intent="ROUTE",
                items=[],
                routes=[],
                answer="외부 장소 검색 기능이 연결되지 않았습니다.",
            )
        if not self._place_search_tool.enabled:
            return AgentChatResponse(
                intent="ROUTE",
                items=[],
                routes=[],
                answer=(
                    "외부 장소를 검색하려면 Go-LeGo-Agent의 .env에 "
                    "KAKAO_REST_API_KEY를 설정해야 합니다."
                ),
            )

        resolved: dict[str, PlaceCandidate] = {}
        for name in external_names:
            try:
                candidates = await self._place_search_tool.execute(name)
            except (httpx.HTTPError, RuntimeError):
                return AgentChatResponse(
                    intent="ROUTE",
                    items=[],
                    routes=[],
                    answer=(
                        f"'{name}' 장소 검색에 실패했습니다. "
                        "Kakao REST API 키와 네트워크 연결을 확인해 주세요."
                    ),
                )

            if not candidates:
                return AgentChatResponse(
                    intent="ROUTE",
                    items=[],
                    routes=[],
                    answer=(
                        f"'{name}'에 해당하는 장소를 찾지 못했습니다. "
                        "역 이름이나 지역명을 포함해 더 구체적으로 입력해 주세요."
                    ),
                )

            normalized_query = self._normalize_place_text(name)
            exact = [
                item for item in candidates
                if self._normalize_place_text(item.name) == normalized_query
            ]
            if len(exact) == 1:
                resolved[name] = exact[0]
                continue
            if len(candidates) == 1:
                resolved[name] = candidates[0]
                continue

            options = []
            for index, item in enumerate(candidates[:3], start=1):
                address = item.road_address or item.address or "주소 정보 없음"
                options.append(f"{index}. {item.name} — {address}")
            return AgentChatResponse(
                intent="ROUTE",
                items=[],
                routes=[],
                answer=(
                    f"'{name}'과 일치할 수 있는 장소가 여러 개 있습니다. "
                    "아래 중 정확한 장소를 골라 다시 입력해 주세요.\n"
                    + "\n".join(options)
                ),
            )

        descriptions = []
        if start_name in resolved:
            place = resolved[start_name]
            descriptions.append(
                f"출발지: {place.name} ({place.road_address or place.address or '주소 정보 없음'})"
            )
        else:
            descriptions.append(f"출발지: {start_name}")
        if destination_name in resolved:
            place = resolved[destination_name]
            descriptions.append(
                f"목적지: {place.name} ({place.road_address or place.address or '주소 정보 없음'})"
            )
        else:
            descriptions.append(f"목적지: {destination_name}")

        return AgentChatResponse(
            intent="ROUTE",
            items=[],
            routes=[],
            answer=(
                "장소 검색으로 다음 위치를 확인했습니다.\n"
                + "\n".join(descriptions)
                + "\n\n현재는 외부 장소 확인 단계까지 연결되어 있습니다. "
                "외부 보행 경로와 캠퍼스 내부 접근성 경로를 안전하게 결합하는 기능은 "
                "아직 구현되지 않아, 검증되지 않은 경로를 임의로 안내하지 않았습니다."
            ),
        )

    @staticmethod
    def _normalize_place_text(value: str) -> str:
        """장소명 비교를 위해 공백과 구분 문자를 정규화합니다."""
        return re.sub(r"[\\s_()·-]", "", value).lower()

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

        mobility_label = {
            "wheelchair": "휠체어",
            "walking": "일반",
            "stroller": "유모차",
            "senior": "어르신",
        }.get(mobility_type, "일반")

        first = routes[0]
        danger_text = (
            f"위험 지점 {first.danger_count}곳이 감지되었습니다."
            if first.danger_count
            else "응답에 포함된 위험 지점은 없습니다."
        )
        return (
            f"{destination_name}까지 {mobility_label} 이동 경로 {len(routes)}개를 확인했습니다. "
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
