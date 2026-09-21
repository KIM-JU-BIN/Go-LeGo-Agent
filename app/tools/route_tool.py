"""Go-LeGo 경로 API를 Agent Tool로 노출합니다."""

from app.domain.route import RouteOption
from app.domain.route_ports import RouteRepository


class RouteSearchTool:
    """자연어 Agent가 접근성 경로를 조회할 수 있도록 RouteRepository를 감쌉니다."""

    name = "find_accessible_route"
    description = (
        "출발지와 목적지 사이의 휠체어 등 이동 유형별 접근성 경로를 조회합니다."
    )

    def __init__(self, repository: RouteRepository) -> None:
        """경로 조회 Repository를 주입받습니다."""
        self._repository = repository

    async def execute(
        self,
        start_name: str,
        destination_name: str,
        mobility_type: str,
        start_latitude: float | None = None,
        start_longitude: float | None = None,
        destination_latitude: float | None = None,
        destination_longitude: float | None = None,
    ) -> list[RouteOption]:
        """Go-LeGo 경로 API를 통해 검증된 경로 목록을 반환합니다."""
        return await self._repository.find_routes(
            start_name=start_name,
            destination_name=destination_name,
            mobility_type=mobility_type,
            start_latitude=start_latitude,
            start_longitude=start_longitude,
            destination_latitude=destination_latitude,
            destination_longitude=destination_longitude,
        )
