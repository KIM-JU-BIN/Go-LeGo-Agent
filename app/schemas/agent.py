"""Agent API의 요청/응답 계약을 정의합니다."""

from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

MobilityType = Literal["walking", "wheelchair", "stroller", "senior"]


class AgentChatRequest(BaseModel):
    """사용자가 Agent에 보내는 질문을 검증합니다."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    message: str = Field(
        min_length=1,
        max_length=200,
        description="사용자의 자연어 질문",
    )
    mobility_type: MobilityType = Field(
        default="walking",
        validation_alias=AliasChoices("mobility_type", "mobilityType"),
        description="이동 유형",
    )


class FacilityItem(BaseModel):
    """Agent가 조회한 접근성 시설 하나를 표현합니다."""

    id: int
    name: str
    type: str
    floor: str = ""
    description: str = ""
    wheelchair_access_status: Literal[
        "ACCESSIBLE",
        "NOT_ACCESSIBLE",
        "UNKNOWN",
    ] = Field(
        default="UNKNOWN",
        serialization_alias="wheelchairAccessStatus",
    )
    latitude: float | None = None
    longitude: float | None = None


class AgentChatResponse(BaseModel):
    """Agent 질문 처리 결과의 외부 API 계약입니다."""

    ok: bool = True
    intent: str
    items: list[FacilityItem] = Field(default_factory=list)
    answer: str


class AgentErrorResponse(BaseModel):
    """Agent API 오류를 일관된 형태로 전달합니다."""

    ok: bool = False
    error: str
    detail: str | None = None
