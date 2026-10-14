"""카카오 로컬 API를 이용해 사용자가 말한 외부 장소를 검색합니다."""

from dataclasses import dataclass

import httpx

from app.core.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class PlaceCandidate:
    """장소 검색 결과에서 확인된 장소명과 좌표만 보관합니다."""

    name: str
    address: str
    road_address: str
    latitude: float
    longitude: float
    place_url: str = ""


class PlaceSearchTool:
    """외부 장소명을 카카오 로컬 검색 API로 실제 장소 후보에 매핑합니다."""

    name = "search_place"
    description = "외부 장소명, 지하철역, 주소를 검색해 실제 장소와 좌표를 확인합니다."
    ENDPOINT = "https://dapi.kakao.com/v2/local/search/keyword.json"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        """서버용 Kakao REST API 키가 설정되어 있는지 반환합니다."""
        return bool(self._settings.kakao_rest_api_key.strip())

    async def execute(self, query: str, size: int = 5) -> list[PlaceCandidate]:
        """검색어로 장소를 찾고 API가 반환한 좌표를 검증해 반환합니다."""
        normalized_query = query.strip()
        if not normalized_query:
            return []
        if not self.enabled:
            raise RuntimeError(
                "KAKAO_REST_API_KEY가 설정되지 않아 외부 장소 검색을 사용할 수 없습니다."
            )

        headers = {
            "Authorization": f"KakaoAK {self._settings.kakao_rest_api_key.strip()}",
        }
        params = {
            "query": normalized_query,
            "size": max(1, min(size, 5)),
            "sort": "accuracy",
        }
        async with httpx.AsyncClient(timeout=self._settings.route_api_timeout_seconds) as client:
            response = await client.get(self.ENDPOINT, headers=headers, params=params)
            response.raise_for_status()
            payload = response.json()

        candidates: list[PlaceCandidate] = []
        for item in payload.get("documents", []):
            if not isinstance(item, dict):
                continue
            try:
                longitude = float(item["x"])
                latitude = float(item["y"])
            except (KeyError, TypeError, ValueError):
                continue
            if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
                continue
            candidates.append(
                PlaceCandidate(
                    name=str(item.get("place_name") or "").strip(),
                    address=str(item.get("address_name") or "").strip(),
                    road_address=str(item.get("road_address_name") or "").strip(),
                    latitude=latitude,
                    longitude=longitude,
                    place_url=str(item.get("place_url") or "").strip(),
                )
            )
        return [candidate for candidate in candidates if candidate.name]
