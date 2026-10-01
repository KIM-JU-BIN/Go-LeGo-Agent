"""OpenAI Responses API를 이용한 자연어 Intent 분석을 제공합니다."""

import logging
from typing import Protocol

from openai import AsyncOpenAI, OpenAIError
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.schemas.agent import AgentIntent, MobilityType

logger = logging.getLogger(__name__)


class LLMIntentProvider(Protocol):
    """Agent가 사용할 수 있는 LLM Intent 분석기의 공통 인터페이스입니다."""

    async def classify(
        self,
        message: str,
        mobility_type: MobilityType,
    ) -> AgentIntent | None:
        """자연어 질문을 구조화된 Agent Intent로 변환합니다."""


class OpenAILLMIntentService:
    """OpenAI Structured Outputs로 자연어 질문을 안전하게 구조화합니다."""

    SYSTEM_PROMPT = """
당신은 Go-LeGo 접근성 Agent의 Intent 분석기입니다.

당신의 역할은 사용자의 자연어 질문을 현재 Agent가 실행할 수 있는 구조로만 변환하는 것입니다.
시설 위치, 접근성 상태, 경로 거리, 위험 여부 등의 사실을 직접 생성하지 마세요.
그런 정보는 이후 Tool과 Backend가 조회합니다.

지원 Intent:
- TOILET: 장애인 화장실
- ELEVATOR: 엘리베이터
- RAMP: 경사로
- STAIR: 계단
- PHOTO: 건물/POI 사진
- ROUTE: 출발지에서 목적지까지 경로
- UNKNOWN: 현재 Agent가 처리할 수 없는 질문

현재 지원 건물:
정보문화관, 본관, 도서관, 디자인관, 운동장, 교수회관

규칙:
1. 건물명은 위 목록에 있는 경우에만 building_names/start_name/destination_name에 넣습니다.
2. 사용자가 '여기', '지금 여기'처럼 현재 위치를 출발지로 표현하면 start_name은 '현재위치'입니다.
3. 사진 위치 키워드는 정문, 후문, 입구, 출입구 중 하나만 사용하고, 없으면 null입니다.
4. 지원 범위 밖의 질문은 UNKNOWN으로 반환합니다.
5. 정보가 부족하면 값을 추측하지 말고 null 또는 빈 배열을 사용합니다.
6. 입력으로 제공된 mobility_type은 이미 UI에서 선택된 값이므로 변경하지 않습니다.
""".strip()

    def __init__(self, settings: Settings | None = None) -> None:
        """환경 설정을 읽고 OpenAI 비동기 클라이언트를 준비합니다."""
        self._settings = settings or get_settings()
        self._client = (
            AsyncOpenAI(
                api_key=self._settings.openai_api_key,
                timeout=self._settings.openai_timeout_seconds,
            )
            if self._settings.openai_api_key
            else None
        )

    @property
    def enabled(self) -> bool:
        """OpenAI API Key가 설정되어 LLM 분석을 사용할 수 있는지 반환합니다."""
        return self._client is not None

    async def classify(
        self,
        message: str,
        mobility_type: MobilityType,
    ) -> AgentIntent | None:
        """사용자 질문을 Structured Output으로 분석하고 실패 시 None을 반환합니다."""
        if self._client is None:
            return None

        prompt = (
            f"선택된 mobility_type: {mobility_type}\n"
            f"사용자 질문: {message}"
        )

        try:
            response = await self._client.responses.parse(
                model=self._settings.openai_model,
                instructions=self.SYSTEM_PROMPT,
                input=prompt,
                text_format=AgentIntent,
            )
        except (OpenAIError, ValidationError) as exc:
            logger.warning("LLM intent analysis failed: %s", exc)
            return None

        return response.output_parsed

    async def close(self) -> None:
        """애플리케이션 종료 시 OpenAI HTTP 클라이언트를 정리합니다."""
        if self._client is not None:
            await self._client.close()
