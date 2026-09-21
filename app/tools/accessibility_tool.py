"""접근성 시설 검색 Tool입니다."""

from app.domain.accessibility import AccessibilityFacility
from app.domain.ports import AccessibilityRepository


class AccessibilitySearchTool:
    """접근성 시설과 등록 사진 검색을 Agent가 사용할 수 있게 노출합니다."""

    name = "search_accessibility_facility"
    description = (
        "등록된 장애인 화장실, 엘리베이터, 경사로, 계단의 위치와 "
        "접근성 상태 또는 POI 사진을 조회합니다."
    )

    def __init__(self, repository: AccessibilityRepository) -> None:
        """Tool이 사용할 데이터 저장소를 주입받습니다."""
        self._repository = repository

    async def execute(
        self,
        intent: str,
        building_names: list[str],
        keyword: str | None = None,
    ) -> list[AccessibilityFacility]:
        """시설 또는 사진 검색을 저장소에 위임하고 결과를 반환합니다."""
        return await self._repository.search_facilities(
            intent,
            building_names,
            keyword,
        )
