"""접근성 Agent의 핵심 유스케이스를 담당합니다."""

from app.application.intent_service import IntentService
from app.domain.accessibility import AccessibilityFacility
from app.domain.ports import AccessibilityRepository
from app.schemas.agent import AgentChatResponse, FacilityItem


class AgentService:
    """질문 분석부터 도메인 조회와 안전한 응답 생성까지 오케스트레이션합니다."""

    def __init__(self, repository: AccessibilityRepository, intent_service: IntentService) -> None:
        """Agent가 사용할 저장소와 의도 분석 서비스를 주입받습니다."""
        self._repository = repository
        self._intent_service = intent_service

    async def chat(self, message: str, mobility_type: str) -> AgentChatResponse:
        """사용자 질문을 처리하고 검증된 시설 데이터만 응답으로 반환합니다."""
        intent = self._intent_service.detect_intent(message)
        if intent is None:
            return AgentChatResponse(
                intent="UNKNOWN",
                items=[],
                answer=(
                    "찾으려는 시설을 조금 더 구체적으로 말씀해 주세요.\\n\\n"
                    "예: 정보문화관 장애인 화장실, 본관 엘리베이터, 도서관 경사로"
                ),
            )

        buildings = self._intent_service.extract_buildings(message)
        facilities = await self._repository.search_facilities(intent, buildings)
        return AgentChatResponse(
            intent=intent,
            items=[self._to_item(facility) for facility in facilities],
            answer=self._build_answer(intent, facilities, mobility_type),
        )

    def _build_answer(self, intent: str, facilities: list[AccessibilityFacility], mobility_type: str) -> str:
        """조회 결과를 사용자에게 보여줄 안전한 자연어 응답으로 변환합니다."""
        labels = {
            "TOILET": "장애인 화장실",
            "ELEVATOR": "엘리베이터",
            "RAMP": "경사로",
            "STAIR": "계단",
        }
        label = labels.get(intent, "시설")
        if not facilities:
            return (
                f"등록된 데이터에서 요청하신 {label} 정보를 찾지 못했습니다.\\n\\n"
                "정확하지 않은 위치를 만들어 안내하지 않습니다. 현장 확인 후 접근성 제보로 등록해 주세요."
            )

        lines = [f"등록된 {label} {len(facilities)}곳을 찾았습니다.", ""]
        for index, facility in enumerate(facilities, start=1):
            lines.append(f"{index}. {facility.name}")
            location = facility.floor or "층 정보 없음"
            if facility.description:
                location += f" / {facility.description}"
            lines.append(f"- 위치: {location}")
            lines.append(f"- 휠체어 접근 상태: {self._accessibility_label(facility.wheelchair_access_status)}")
            lines.append("")

        if mobility_type == "wheelchair":
            lines.append("휠체어 이동 안내: UNKNOWN 상태는 현장 확인이 필요합니다.")
        else:
            lines.append("필요하면 휠체어 모드로 전환해 접근성 상태를 함께 확인할 수 있습니다.")
        return "\\n".join(lines).strip()

    @staticmethod
    def _accessibility_label(status: str) -> str:
        """접근성 상태 코드를 사용자용 문구로 변환합니다."""
        labels = {
            "ACCESSIBLE": "확인됨 (ACCESSIBLE)",
            "NOT_ACCESSIBLE": "접근 어려움 (NOT_ACCESSIBLE)",
            "UNKNOWN": "확인 필요 (UNKNOWN)",
        }
        return labels.get(status, "확인 필요 (UNKNOWN)")

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
        )
