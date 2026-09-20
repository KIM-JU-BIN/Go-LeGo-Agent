"""의도 분석 서비스 단위 테스트입니다."""

from app.application.intent_service import IntentService


def test_detect_toilet_intent() -> None:
    """장애인 화장실 질문을 TOILET 의도로 분류하는지 검증합니다."""
    service = IntentService()
    assert service.detect_intent("정보문화관 장애인 화장실 어디 있어?") == "TOILET"


def test_extract_building_normalizes_school_name() -> None:
    """학교명이 붙은 건물명도 동일 건물로 추출하는지 검증합니다."""
    service = IntentService()
    assert service.extract_buildings("한양여자대학교 정보문화관 엘리베이터") == ["정보문화관"]


def test_unknown_intent_returns_none() -> None:
    """지원하지 않는 질문은 의도를 임의로 생성하지 않는지 검증합니다."""
    service = IntentService()
    assert service.detect_intent("오늘 날씨 어때?") is None
