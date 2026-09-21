"""접근성 경로 도메인의 불변 모델을 정의합니다."""


from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RoutePoint:
    """경로 위의 한 지점을 표현합니다."""

    id: str
    name: str
    latitude: float
    longitude: float
    type: str


@dataclass(frozen=True, slots=True)
class RouteFeatures:
    """경로에서 확인된 접근성 관련 시설 개수를 표현합니다."""

    stairs: int = 0
    ramps: int = 0
    elevators: int = 0
    crosswalks: int = 0


@dataclass(frozen=True, slots=True)
class RouteOption:
    """Go-LeGo 백엔드가 계산한 하나의 경로 선택지를 표현합니다."""

    id: str
    title: str
    distance: float
    duration: float
    danger_count: int
    features: RouteFeatures
    path: tuple[RoutePoint, ...]
