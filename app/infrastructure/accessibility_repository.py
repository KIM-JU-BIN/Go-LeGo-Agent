"""현재 Go-LeGo Agent MVP의 MySQL 저장소 구현체입니다."""

from app.core.database import fetch_all
from app.domain.accessibility import AccessibilityFacility
from app.domain.ports import AccessibilityRepository


class MySQLAccessibilityRepository(AccessibilityRepository):
    """기존 barrier_free_db 스키마를 조회하는 MySQL 어댑터입니다."""

    async def search_facilities(
        self,
        intent: str,
        building_names: list[str],
    ) -> list[AccessibilityFacility]:
        """기존 POI/facility/place_accessibility 테이블에서 시설을 조회합니다."""
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
                pa.wheelchair_access_status
            FROM poi p
            LEFT JOIN place_accessibility pa ON pa.poi_id = p.poi_id
            WHERE p.poi_type IN ({placeholders})
            ORDER BY p.poi_name ASC
        """
        rows = await fetch_all(query, tuple(poi_types))

        facilities = [self._to_domain(row) for row in rows]
        if not building_names:
            return facilities[:5]

        # DB 스키마에 건물 전용 컬럼이 없으므로 기존 MVP와 동일하게
        # POI 이름/설명에 건물명이 포함되는지를 기준으로 후보를 좁힙니다.
        normalized_buildings = [self._normalize(name) for name in building_names]
        ranked = []
        for facility in facilities:
            haystack = self._normalize(
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
        return AccessibilityFacility(
            id=str(row["poi_id"]),
            name=str(row.get("poi_name") or ""),
            type=str(row.get("poi_type") or ""),
            floor=str(row.get("floor_info") or ""),
            description=str(row.get("description") or ""),
            wheelchair_access_status=status,
            latitude=float(row["latitude"]) if row.get("latitude") is not None else None,
            longitude=float(row["longitude"]) if row.get("longitude") is not None else None,
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
