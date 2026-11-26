"""자연어 질문에서 Agent가 사용할 의도와 장소명을 추출합니다."""

import re


class IntentService:
    """현재 MVP에서 사용할 접근성 시설, 사진, 경로 의도를 판별합니다."""

    BUILDINGS = ("정보문화관", "본관", "도서관", "디자인관", "운동장", "교수회관")

    # 불편 구간 제보 화면의 유형 칩(report.html)과 동일한 값을 사용해야 자동 선택이 됩니다.
    REPORT_TYPE_DEFAULT = "기타"
    REPORT_TYPE_RULES = (
        ("급경사", r"급경사|경사가|가파"),
        ("파손 보도", r"파손|깨졌|깨진|보도블|패였|구멍"),
        ("단차", r"단차|턱"),
        ("미끄러운 노면", r"미끄|빙판|결빙"),
        ("공사 통제", r"공사|통제|막혔|막혀|막힘|폐쇄"),
    )

    def detect_intent(self, message: str) -> str | None:
        """질문에서 지원하는 시설, 사진 또는 경로 의도를 하나 선택합니다."""
        text = self._normalize(message)
        # 제보 표현은 "보여줘" 같은 사진 표현보다 먼저 확인해야 오분류되지 않습니다.
        if self._looks_like_report(text):
            return "REPORT"
        if self._looks_like_photo_question(text):
            return "PHOTO"
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
        return [building for building in self.BUILDINGS if self._normalize(building) in normalized]

    def extract_route_endpoints(self, message: str) -> tuple[str | None, str | None]:
        """질문에서 경로 출발지와 목적지 건물명을 문장 순서대로 추출합니다."""
        normalized = self._normalize(message)
        matches = [
            (normalized.find(self._normalize(building)), building)
            for building in self.BUILDINGS
            if self._normalize(building) in normalized
        ]
        matches.sort(key=lambda item: item[0])

        buildings = [building for _, building in matches]
        if len(buildings) >= 2:
            return buildings[0], buildings[1]
        if len(buildings) == 1:
            return "현재위치", buildings[0]
        return None, None

    def extract_report_draft(self, message: str) -> tuple[str | None, str]:
        """제보 문장에서 장소(건물명)와 제보 유형 초안을 추출합니다.

        장소를 알 수 없으면 None, 유형을 알 수 없으면 "기타"를 반환합니다.
        """
        buildings = self.extract_buildings(message)
        place_name = buildings[0] if buildings else None

        normalized = self._normalize(message)
        for report_type, pattern in self.REPORT_TYPE_RULES:
            if re.search(pattern, normalized):
                return place_name, report_type
        return place_name, self.REPORT_TYPE_DEFAULT

    @staticmethod
    def _looks_like_report(text: str) -> bool:
        """불편 구간 제보 의도를 판별합니다.

        "제보/신고" 같은 명시적 표현이거나, 이미 발생한 문제를 서술하는 표현만 인정합니다.
        ("위험한 곳 피해서 가는 길" 같은 경로 질문이 제보로 분류되지 않도록 문제 표현을 좁게 잡음)
        """
        if re.search(r"제보|신고|민원", text):
            return True
        return bool(
            re.search(
                r"막혔|막혀있|막혀서|막혀요|파손|깨졌|깨진|고장났|고장나|고장이|"
                r"단차가|미끄러워|공사중이|통제중|불편해|불편한데",
                text,
            )
        )

    @staticmethod
    def extract_photo_keyword(message: str) -> str | None:
        """사진 질문에서 정문 등 구체적인 위치 키워드를 추출합니다."""
        normalized = IntentService._normalize(message)
        for keyword in ("정문", "후문", "입구", "출입구"):
            if keyword in normalized:
                return keyword
        return None

    @staticmethod
    def _looks_like_photo_question(text: str) -> bool:
        """사진이나 이미지를 요청하는 표현을 판별합니다."""
        return bool(re.search(r"사진|이미지|파노라마|모습|보여줘|보여", text))

    @staticmethod
    def _looks_like_route_question(text: str) -> bool:
        """경로 탐색 질문의 다양한 표현을 판별합니다."""
        return bool(
            re.search(
                r"경로|길찾기|가는길|가는법|가는방법|어떻게가|어떻게가는|갈수|이동|찾아가|찾아가는|까지|에서.+로|route",
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
