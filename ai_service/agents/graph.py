"""
ai_service/agents/graph.py — Multi-Agent ReAct StateGraph compilation with Persistent Memory.

ReAct workflow:
START -> Supervisor <-> ToolNode -> END
All comments and docstrings are in English.
"""

import logging

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from ai_service.agents.memory import get_checkpointer
from ai_service.agents.state import StudyDockState
from ai_service.agents.supervisor import SUPERVISOR_TOOLS, supervisor_node

logger = logging.getLogger(__name__)


def build_study_graph():
    """
    Build and compile the Multi-Agent Study Dock ReAct graph with checkpointer.
    """
    workflow = StateGraph(StudyDockState)

    # 1. Register Supervisor and Tool execution nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("tools", ToolNode(SUPERVISOR_TOOLS))

    # 2. Entry point -> Supervisor
    workflow.add_edge(START, "supervisor")

    # 3. Conditional routing:
    # If the Supervisor emitted tool calls, route to "tools"; otherwise route to END.
    workflow.add_conditional_edges("supervisor", tools_condition)

    # 4. Tool execution returns to Supervisor to synthesize the grounded answer
    workflow.add_edge("tools", "supervisor")

    # 5. Compile with persistent checkpointer (PostgresSaver / MemorySaver)
    checkpointer = get_checkpointer()
    compiled = workflow.compile(checkpointer=checkpointer)
    logger.info("[Graph] Successfully compiled LangGraph v2 with checkpointer.")
    return compiled


# Module-level singleton
_compiled_study_graph = None


def get_study_graph():
    """Get or initialize the compiled LangGraph singleton."""
    global _compiled_study_graph
    if _compiled_study_graph is None:
        _compiled_study_graph = build_study_graph()
    return _compiled_study_graph
