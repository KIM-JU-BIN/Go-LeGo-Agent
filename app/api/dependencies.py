"""FastAPI 의존성 주입 객체를 중앙에서 구성합니다."""

from functools import lru_cache

from app.application.agent_service import AgentService
from app.application.intent_service import IntentService
from app.infrastructure.accessibility_repository import MySQLAccessibilityRepository
from app.infrastructure.route_repository import GoLegoRouteRepository
from app.tools.accessibility_tool import AccessibilitySearchTool
from app.tools.route_tool import RouteSearchTool


@lru_cache(maxsize=1)
def get_intent_service() -> IntentService:
    """애플리케이션 전체에서 공유할 IntentService를 반환합니다."""
    return IntentService()


@lru_cache(maxsize=1)
def get_accessibility_repository() -> MySQLAccessibilityRepository:
    """현재 실행 환경에서 사용할 MySQL 저장소 Adapter를 반환합니다."""
    return MySQLAccessibilityRepository()


@lru_cache(maxsize=1)
def get_accessibility_search_tool() -> AccessibilitySearchTool:
    """접근성 검색 Tool과 저장소 Adapter를 조립해 반환합니다."""
    return AccessibilitySearchTool(get_accessibility_repository())


@lru_cache(maxsize=1)
def get_route_repository() -> GoLegoRouteRepository:
    """기존 Go-LeGo 백엔드 경로 API Adapter를 반환합니다."""
    return GoLegoRouteRepository()


@lru_cache(maxsize=1)
def get_route_search_tool() -> RouteSearchTool:
    """경로 조회 Tool과 Go-LeGo API Adapter를 조립해 반환합니다."""
    return RouteSearchTool(get_route_repository())


@lru_cache(maxsize=1)
def get_agent_service() -> AgentService:
    """HTTP 계층에서 사용할 AgentService 의존성을 조립해 반환합니다."""
    return AgentService(
        search_tool=get_accessibility_search_tool(),
        intent_service=get_intent_service(),
        route_tool=get_route_search_tool(),
    )
