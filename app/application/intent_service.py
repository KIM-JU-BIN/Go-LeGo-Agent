"""자연어 질문에서 Agent가 사용할 의도와 장소명을 추출합니다."""

import re


class IntentService:
    """현재 MVP에서 사용할 접근성 시설과 경로 의도를 판별합니다."""

    BUILDINGS = ("정보문화관", "본관", "도서관", "디자인관", "운동장", "교수회관")

    def detect_intent(self, message: str) -> str | None:
        """질문에서 지원하는 시설 또는 경로 의도를 하나 선택합니다."""
        text = self._normalize(message)
        if re.search(r"화장실|toilet", text):
            return "TOILET"
        if re.search(r"엘리베이터|엘베|승강기", text):
            return "ELEVATOR"
        if re.search(r"경사로|램프|ramp", text):
            return "RAMP"
        if re.search(r"계단|stair", text):
            return "STAIR"
        if self._looks_like_route_question(text):
            return "ROUTE"
        return None

    def extract_buildings(self, message: str) -> list[str]:
        """질문에 포함된 알려진 건물명을 추출합니다."""
        normalized = self._normalize(message)
        return [
            building
            for building in self.BUILDINGS
            if self._normalize(building) in normalized
        ]

    def extract_route_endpoints(self, message: str) -> tuple[str | None, str | None]:
        """질문에서 경로 출발지와 목적지 건물명을 순서대로 추출합니다."""
        buildings = self.extract_buildings(message)
        if len(buildings) >= 2:
            return buildings[0], buildings[1]
        if len(buildings) == 1:
            return "현재위치", buildings[0]
        return None, None

    @staticmethod
    def _looks_like_route_question(text: str) -> bool:
        """경로 탐색 질문의 대표적인 표현을 판별합니다."""
        return bool(
            re.search(
                r"경로|길찾기|가는길|가는길|어떻게가|갈수|이동|까지|에서.+까지|route",
                text,
            )
        )

    @staticmethod
    def _normalize(value: str) -> str:
        """자연어 검색 비교를 위한 문자열 정규화를 수행합니다."""
        normalized = str(value or "")
        normalized = normalized.replace("한양여자대학교", "")
        normalized = normalized.replace("한양여대", "")
        return re.sub(r"[\s_()-]", "", normalized).lower()
