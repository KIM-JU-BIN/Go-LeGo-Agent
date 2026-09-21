"""현재 Go-LeGo Agent MVP의 MySQL 저장소 구현체입니다."""

from urllib.parse import urljoin

from app.core.config import get_settings
from app.core.database import fetch_all
from app.domain.accessibility import AccessibilityFacility
from app.domain.ports import AccessibilityRepository


class MySQLAccessibilityRepository(AccessibilityRepository):
    """기존 barrier_free_db 스키마를 조회하는 MySQL 어댑터입니다."""

    async def search_facilities(
        self,
        intent: str,
        building_names: list[str],
        keyword: str | None = None,
    ) -> list[AccessibilityFacility]:
        """기존 POI/facility/place_accessibility 테이블에서 시설을 조회합니다."""
        if intent == "PHOTO":
            return await self._search_photos(building_names, keyword)

        poi_types = {
            "TOILET": ["accessible_toilet"],
            "ELEVATOR": ["elevator"],
            "RAMP": ["ramp"],
            "STAIR": ["stair"],
        }.get(intent, [])
        if not poi_types:
            return []

        placeholders = ", ".join("%s" for _ in poi_types)
        query = f"""
            SELECT
                p.poi_id,
                p.poi_name,
                p.poi_type,
                p.latitude,
                p.longitude,
                p.floor_info,
                p.description,
                p.photo_url,
                pa.wheelchair_access_status
            FROM poi p
            LEFT JOIN place_accessibility pa ON pa.poi_id = p.poi_id
            WHERE p.poi_type IN ({placeholders})
            ORDER BY p.poi_name ASC
        """
        rows = await fetch_all(query, tuple(poi_types))

        facilities = [self._to_domain(row) for row in rows]
        return self._filter_by_buildings(facilities, building_names)

    async def _search_photos(
        self,
        building_names: list[str],
        keyword: str | None,
    ) -> list[AccessibilityFacility]:
        """사진이 등록된 POI를 건물명과 키워드로 좁혀 조회합니다."""
        query = """
            SELECT
                p.poi_id,
                p.poi_name,
                p.poi_type,
                p.latitude,
                p.longitude,
                p.floor_info,
                p.description,
                p.photo_url,
                pa.wheelchair_access_status
            FROM poi p
            LEFT JOIN place_accessibility pa ON pa.poi_id = p.poi_id
            WHERE p.photo_url IS NOT NULL
            ORDER BY p.poi_name ASC
        """
        rows = await fetch_all(query)
        facilities = [self._to_domain(row) for row in rows]

        normalized_buildings = [self._normalize(name) for name in building_names]
        normalized_keyword = self._normalize(keyword or "")
        ranked: list[tuple[int, AccessibilityFacility]] = []

        for facility in facilities:
            haystack = self._normalize(
                " ".join(
                    filter(
                        None,
                        [facility.name, facility.description, facility.floor],
                    )
                )
            )
            score = 0
            if normalized_buildings:
                score += sum(
                    10 for name in normalized_buildings if name and name in haystack
                )
            if normalized_keyword and normalized_keyword in haystack:
                score += 30
            if score:
                ranked.append((score, facility))

        ranked.sort(key=lambda item: (-item[0], item[1].name))
        return [facility for _, facility in ranked[:5]]

    @staticmethod
    def _filter_by_buildings(
        facilities: list[AccessibilityFacility],
        building_names: list[str],
    ) -> list[AccessibilityFacility]:
        """건물명이 지정된 경우 POI 이름과 설명을 기준으로 후보를 좁힙니다."""
        if not building_names:
            return facilities[:5]

        normalized_buildings = [
            MySQLAccessibilityRepository._normalize(name)
            for name in building_names
        ]
        ranked = []
        for facility in facilities:
            haystack = MySQLAccessibilityRepository._normalize(
                " ".join(
                    filter(
                        None,
                        [facility.name, facility.description, facility.floor],
                    )
                )
            )
            score = sum(10 for name in normalized_buildings if name in haystack)
            if score > 0:
                ranked.append((score, facility))

        ranked.sort(key=lambda item: (-item[0], item[1].name))
        return [facility for _, facility in ranked[:5]]

    @staticmethod
    def _to_domain(row: dict) -> AccessibilityFacility:
        """DB 한 행을 도메인 모델로 변환합니다."""
        status = row.get("wheelchair_access_status") or "UNKNOWN"
        if status not in {"ACCESSIBLE", "NOT_ACCESSIBLE", "UNKNOWN"}:
            status = "UNKNOWN"

        photo_url = row.get("photo_url")
        if photo_url:
            photo_url = urljoin(
                f"{get_settings().golego_backend_base_url}/",
                str(photo_url),
            )

        return AccessibilityFacility(
            id=str(row["poi_id"]),
            name=str(row.get("poi_name") or ""),
            type=str(row.get("poi_type") or ""),
            floor=str(row.get("floor_info") or ""),
            description=str(row.get("description") or ""),
            wheelchair_access_status=status,
            latitude=float(row["latitude"]) if row.get("latitude") is not None else None,
            longitude=float(row["longitude"]) if row.get("longitude") is not None else None,
            photo_url=photo_url,
        )

    @staticmethod
    def _normalize(value: str) -> str:
        """검색 비교를 위해 건물명과 설명의 공백/학교명을 정규화합니다."""
        return (
            str(value or "")
            .replace("한양여자대학교", "")
            .replace("한양여대", "")
            .replace(" ", "")
            .replace("_", "")
            .replace("(", "")
            .replace(")", "")
            .replace("-", "")
            .lower()
        )
