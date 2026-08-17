import logging

from service.ai_core.platform.contracts import AITool

logger = logging.getLogger(__name__)

_AI_TOOLS: dict[str, AITool] = {}


def register_ai_tool(tool: AITool) -> None:
    key = f"{tool.name}:{tool.version}"
    _AI_TOOLS[key] = tool
    # Also register default alias by tool.name
    _AI_TOOLS[tool.name] = tool
    logger.info(f"Registered AI Tool '{tool.name}' (v{tool.version})")


def get_ai_tool(name: str, version: str | None = None) -> AITool:
    if version:
        key = f"{name}:{version}"
        if key in _AI_TOOLS:
            return _AI_TOOLS[key]
    if name in _AI_TOOLS:
        return _AI_TOOLS[name]
    raise KeyError(f"AI Tool '{name}' (version={version}) is not registered.")
