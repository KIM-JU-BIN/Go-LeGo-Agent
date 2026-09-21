"""Agent Tool을 이름으로 관리하기 위한 Registry입니다."""

from typing import Protocol

from app.tools.accessibility_tool import AccessibilitySearchTool
from app.tools.route_tool import RouteSearchTool


class AgentTool(Protocol):
    """Tool Registry에 등록할 수 있는 공통 인터페이스입니다."""

    name: str


class ToolRegistry:
    """Agent가 사용할 Tool을 중앙에서 등록하고 조회합니다."""

    def __init__(
        self,
        accessibility_tool: AccessibilitySearchTool,
        route_tool: RouteSearchTool,
    ) -> None:
        """현재 Agent에서 제공할 Tool을 등록합니다."""
        self._tools: dict[str, AgentTool] = {
            accessibility_tool.name: accessibility_tool,
            route_tool.name: route_tool,
        }

    def get(self, name: str) -> AgentTool:
        """등록된 Tool을 이름으로 반환합니다."""
        return self._tools[name]
