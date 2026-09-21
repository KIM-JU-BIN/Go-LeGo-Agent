"""Go-LeGo Node 백엔드의 접근성 경로 API Adapter입니다."""

import httpx

from app.core.config import get_settings
from app.domain.route import RouteFeatures, RouteOption, RoutePoint
from app.domain.route_ports import RouteRepository


class GoLegoRouteRepository(RouteRepository):
    """기존 Go-LeGo /api/access-routes API를 호출하는 Adapter입니다."""

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
        """Go-LeGo 백엔드에서 이동 유형에 맞는 경로 목록을 조회합니다."""
        settings = get_settings()
        params = {
            "startName": start_name,
            "name": destination_name,
            "mobilityType": mobility_type,
        }
        self._add_point_params(
            params,
            start_latitude,
            start_longitude,
            destination_latitude,
            destination_longitude,
        )

        async with httpx.AsyncClient(
            base_url=settings.golego_backend_base_url,
            timeout=settings.route_api_timeout_seconds,
        ) as client:
            response = await client.get("/api/access-routes", params=params)
            response.raise_for_status()
            payload = response.json()

        if not payload.get("ok"):
            return []

        return [
            self._to_domain(item)
            for item in payload.get("routes", [])
            if isinstance(item, dict)
        ]

    @staticmethod
    def _add_point_params(
        params: dict[str, str],
        start_latitude: float | None,
        start_longitude: float | None,
        destination_latitude: float | None,
        destination_longitude: float | None,
    ) -> None:
        """선택적으로 출발지와 목적지 좌표를 Go-LeGo API 파라미터에 추가합니다."""
        if start_latitude is not None and start_longitude is not None:
            params["startY"] = str(start_latitude)
            params["startX"] = str(start_longitude)
        if destination_latitude is not None and destination_longitude is not None:
            params["y"] = str(destination_latitude)
            params["x"] = str(destination_longitude)

    @staticmethod
    def _to_domain(item: dict) -> RouteOption:
        """Go-LeGo 경로 JSON 하나를 도메인 모델로 변환합니다."""
        feature_data = item.get("features") or {}
        path = tuple(
            RoutePoint(
                id=str(point.get("id") or ""),
                name=str(point.get("name") or ""),
                latitude=float(point.get("lat") or 0),
                longitude=float(point.get("lng") or 0),
                type=str(point.get("type") or "path"),
            )
            for point in item.get("path", [])
            if isinstance(point, dict)
        )
        return RouteOption(
            id=str(item.get("id") or ""),
            title=str(item.get("title") or "경로"),
            distance=float(item.get("distance") or 0),
            duration=float(item.get("duration") or 0),
            danger_count=int(item.get("dangerCount") or 0),
            features=RouteFeatures(
                stairs=int(feature_data.get("stairs") or 0),
                ramps=int(feature_data.get("ramps") or 0),
                elevators=int(feature_data.get("elevators") or 0),
                crosswalks=int(feature_data.get("crosswalks") or 0),
            ),
            path=path,
        )
