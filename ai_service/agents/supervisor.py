"""
ai_service/agents/supervisor.py — Backward compatibility facade for General Agent.

Deprecated: Please import directly from `ai_service.agents.general_agent` and `ai_service.agents.router`.
"""

from ai_service.agents.general_agent import GENERAL_AGENT_TOOLS, general_agent_node
from ai_service.agents.router import router_node
from ai_service.connection import get_llm

SUPERVISOR_TOOLS = GENERAL_AGENT_TOOLS
supervisor_node = general_agent_node

__all__ = [
    "GENERAL_AGENT_TOOLS",
    "SUPERVISOR_TOOLS",
    "general_agent_node",
    "get_llm",
    "router_node",
    "supervisor_node",
]
