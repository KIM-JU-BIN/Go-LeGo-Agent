"""Agent Tool을 이름으로 관리하기 위한 Registry입니다."""

from app.tools.accessibility_tool import AccessibilitySearchTool


class ToolRegistry:
    """Agent가 사용할 Tool을 중앙에서 등록하고 조회합니다."""

    def __init__(self, accessibility_tool: AccessibilitySearchTool) -> None:
        """현재 Agent에서 제공할 Tool을 등록합니다."""
        self._tools = {accessibility_tool.name: accessibility_tool}

    def get(self, name: str) -> AccessibilitySearchTool:
        """등록된 Tool을 이름으로 반환합니다."""
        return self._tools[name]
