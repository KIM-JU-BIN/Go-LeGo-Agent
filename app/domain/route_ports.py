"""접근성 경로 조회를 위한 애플리케이션 경계를 정의합니다."""

from abc import ABC, abstractmethod

from app.domain.route import RouteOption


class RouteRepository(ABC):
    """외부 경로 API 구현체가 따라야 하는 저장소 포트입니다."""

    @abstractmethod
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
        """출발지와 목적지의 접근성 경로를 조회합니다."""
        raise NotImplementedError
