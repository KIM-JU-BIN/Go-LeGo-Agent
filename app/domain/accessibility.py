"""접근성 도메인의 불변 모델과 타입을 정의합니다."""

from dataclasses import dataclass
from typing import Literal

AccessibilityStatus = Literal["ACCESSIBLE", "NOT_ACCESSIBLE", "UNKNOWN"]


@dataclass(frozen=True, slots=True)
class AccessibilityFacility:
    """DB나 외부 API에 종속되지 않은 접근성 시설 도메인 모델입니다."""

    id: str
    name: str
    type: str
    floor: str
    description: str
    wheelchair_access_status: AccessibilityStatus
    latitude: float | None
    longitude: float | None
