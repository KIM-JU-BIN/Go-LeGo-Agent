"""애플리케이션 계층이 인프라 구현에 의존하지 않도록 포트를 정의합니다."""

from abc import ABC, abstractmethod

from app.domain.accessibility import AccessibilityFacility


class AccessibilityRepository(ABC):
    """접근성 시설 조회 기능의 저장소 인터페이스입니다.

    현재는 MySQL 구현체를 사용하지만, Go-LeGo 본 프로젝트에 통합할 때는
    기존 Node API를 호출하는 HTTP 어댑터로 교체할 수 있도록 분리합니다.
    """

    @abstractmethod
    async def search_facilities(self, intent: str, building_names: list[str]) -> list[AccessibilityFacility]:
        """의도와 건물 조건에 맞는 접근성 시설을 조회합니다."""
        raise NotImplementedError
