"""불편 구간 제보 의도와 SSE 스트리밍 서비스 단위 테스트입니다."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_agent_service
from app.api.routes.agent import router as agent_router
from app.application.agent_service import AgentService
from app.application.intent_service import IntentService


class _NoopTool:
    """제보/UNKNOWN 질문은 Tool을 호출하지 않으므로 자리만 채우는 대역입니다."""

    async def execute(self, *args, **kwargs):  # pragma: no cover - 호출되면 실패해야 함
        raise AssertionError("제보 질문에서 Tool이 호출되면 안 됩니다.")


def _service() -> AgentService:
    """Tool 없이 동작하는 테스트용 AgentService를 만듭니다."""
    return AgentService(search_tool=_NoopTool(), intent_service=IntentService())


@pytest.mark.parametrize(
    "message",
    [
        "정보문화관 앞 계단이 막혔어",
        "본관 앞 보도블록이 파손됐어 제보할래",
        "도서관 엘리베이터 고장났어",
        "불편 구간 신고하고 싶어",
    ],
)
def test_report_intent_is_detected(message: str) -> None:
    """제보 표현과 문제 상황 서술이 REPORT로 분류되는지 검증합니다."""
    assert IntentService().detect_intent(message) == "REPORT"


@pytest.mark.parametrize(
    "message",
    [
        "정보문화관 장애인 화장실 어디 있어?",
        "본관에서 정보문화관까지 휠체어로 가는 길",
        "위험한 곳 피해서 본관까지 가는 길 알려줘",
        "정보문화관 정문 사진 보여줘",
    ],
)
def test_existing_intents_are_not_hijacked_by_report(message: str) -> None:
    """기존 시설/경로/사진 질문이 REPORT로 잘못 분류되지 않는지 검증합니다."""
    assert IntentService().detect_intent(message) != "REPORT"


def test_report_draft_extracts_place_and_type() -> None:
    """장소와 제보 유형 초안이 report.html 칩 값과 일치하게 추출되는지 검증합니다."""
    service = IntentService()
    assert service.extract_report_draft("정보문화관 앞 계단이 막혔어") == (
        "정보문화관",
        "공사 통제",
    )
    assert service.extract_report_draft("본관 앞 보도블록이 파손됐어") == ("본관", "파손 보도")
    assert service.extract_report_draft("어딘가 불편해") == (None, "기타")


async def test_chat_returns_report_draft_without_tools() -> None:
    """REPORT 응답이 제보 초안을 담고 Tool/DB를 건드리지 않는지 검증합니다."""
    response = await _service().chat("정보문화관 앞 계단이 막혔어", "wheelchair")
    assert response.intent == "REPORT"
    assert response.report is not None
    assert response.report.place_name == "정보문화관"
    assert response.report.report_type == "공사 통제"
    assert response.routes == [] and response.items == []


async def test_chat_stream_emits_steps_then_result() -> None:
    """step 이벤트가 먼저 나오고 마지막이 result 이벤트인지 검증합니다."""
    events = [e async for e in _service().chat_stream("본관 신고할게", "wheelchair")]
    names = [e["event"] for e in events]
    assert names[-1] == "result"
    assert set(names[:-1]) == {"step"} and len(names) >= 3
    result = events[-1]["data"]
    assert result["intent"] == "REPORT"
    assert result["report"]["placeName"] == "본관"
    assert result["report"]["reportType"] == "기타"


def test_stream_endpoint_returns_sse() -> None:
    """HTTP 엔드포인트가 text/event-stream으로 응답하고 camelCase로 직렬화하는지 검증합니다."""
    app = FastAPI()
    app.include_router(agent_router, prefix="/api")
    app.dependency_overrides[get_agent_service] = _service
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/agent/chat/stream",
        json={"message": "도서관 보도블록 파손 제보", "mobilityType": "wheelchair"},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = "".join(response.iter_text())

    blocks = [b for b in body.split("\n\n") if b.strip()]
    assert blocks[0].startswith("event: step")
    last = blocks[-1].split("\n")
    assert last[0] == "event: result"
    payload = json.loads(last[1].removeprefix("data: "))
    assert payload["report"]["reportType"] == "파손 보도"


def test_stream_endpoint_rejects_too_long_message() -> None:
    """스트리밍 엔드포인트도 질문 길이 제한(422)을 동일하게 적용하는지 검증합니다."""
    app = FastAPI()
    app.include_router(agent_router, prefix="/api")
    app.dependency_overrides[get_agent_service] = _service
    response = TestClient(app).post(
        "/api/agent/chat/stream", json={"message": "가" * 201, "mobilityType": "walking"}
    )
    assert response.status_code == 422
