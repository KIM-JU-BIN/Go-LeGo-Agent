"""Agent API의 요청/응답 계약을 정의합니다."""

from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

MobilityType = Literal["walking", "wheelchair", "stroller", "senior"]


class AgentChatRequest(BaseModel):
    """사용자가 Agent에 보내는 질문과 선택적 현재 위치를 검증합니다."""

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
    current_latitude: float | None = Field(
        default=None,
        validation_alias=AliasChoices("current_latitude", "currentLatitude"),
        description="현재 위치의 위도",
    )
    current_longitude: float | None = Field(
        default=None,
        validation_alias=AliasChoices("current_longitude", "currentLongitude"),
        description="현재 위치의 경도",
    )


class FacilityItem(BaseModel):
    """Agent가 조회한 접근성 시설 또는 사진 POI 하나를 표현합니다."""

    id: str
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
    photo_url: str | None = Field(
        default=None,
        serialization_alias="photoUrl",
    )


class RoutePointItem(BaseModel):
    """접근성 경로 위의 한 지점을 API 응답으로 표현합니다."""

    id: str
    name: str
    latitude: float
    longitude: float
    type: str


class RouteFeaturesItem(BaseModel):
    """경로에서 확인된 접근성 관련 시설 개수를 표현합니다."""

    stairs: int = 0
    ramps: int = 0
    elevators: int = 0
    crosswalks: int = 0


class RouteItem(BaseModel):
    """Agent가 조회한 접근성 경로 하나를 표현합니다."""

    id: str
    title: str
    distance: float
    duration: float
    danger_count: int = Field(default=0, serialization_alias="dangerCount")
    features: RouteFeaturesItem = Field(default_factory=RouteFeaturesItem)
    path: list[RoutePointItem] = Field(default_factory=list)


class AgentChatResponse(BaseModel):
    """Agent 질문 처리 결과의 외부 API 계약입니다."""

    ok: bool = True
    intent: str
    items: list[FacilityItem] = Field(default_factory=list)
    routes: list[RouteItem] = Field(default_factory=list)
    answer: str


class AgentErrorResponse(BaseModel):
    """Agent API 오류를 일관된 형태로 전달합니다."""

    ok: bool = False
    error: str
    detail: str | None = None
