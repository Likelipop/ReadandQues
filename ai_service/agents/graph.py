r"""
ai_service/agents/graph.py — Multi-Agent Study Dock StateGraph with Intent Router.

Graph topology:
    START -> router -> general_agent <-> tools -> END
                   \-> quiz_agent -> END
"""

import logging

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from ai_service.agents.general_agent import GENERAL_AGENT_TOOLS, general_agent_node
from ai_service.agents.memory import get_checkpointer
from ai_service.agents.quiz_agent import quiz_agent_node
from ai_service.agents.router import router_node
from ai_service.agents.state import StudyDockState

logger = logging.getLogger(__name__)


def route_by_intent(state: StudyDockState) -> str:
    """Route to the appropriate agent node based on the classified intent."""
    intent = state.get("intent", "general")
    if intent == "quiz":
        return "quiz_agent"
    return "general_agent"


def build_study_graph():
    """
    Build and compile the Multi-Agent Study Dock graph with intent router.

    Topology:
        START -> router_node (LLM intent classification)
              -> [quiz] -> quiz_agent_node -> END
              -> [general] -> general_agent_node <-> tools -> END
    """
    workflow = StateGraph(StudyDockState)

    # 1. Register nodes
    workflow.add_node("router", router_node)
    workflow.add_node("general_agent", general_agent_node)
    workflow.add_node("quiz_agent", quiz_agent_node)
    workflow.add_node("tools", ToolNode(GENERAL_AGENT_TOOLS))

    # 2. Entry point -> Router
    workflow.add_edge(START, "router")

    # 3. Router dispatches based on intent
    workflow.add_conditional_edges("router", route_by_intent, {
        "quiz_agent": "quiz_agent",
        "general_agent": "general_agent",
    })

    # 4. General agent may call tools (ReAct loop)
    workflow.add_conditional_edges("general_agent", tools_condition)

    # 5. Tool results return to general agent for synthesis
    workflow.add_edge("tools", "general_agent")

    # 6. Quiz agent goes directly to END
    workflow.add_edge("quiz_agent", END)

    # 7. Compile with persistent checkpointer
    checkpointer = get_checkpointer()
    compiled = workflow.compile(checkpointer=checkpointer)
    logger.info("[Graph] Successfully compiled Study Dock graph: router -> general_agent/quiz_agent")
    return compiled


# Module-level singleton
_compiled_study_graph = None


def get_study_graph():
    """Get or initialize the compiled LangGraph singleton."""
    global _compiled_study_graph
    if _compiled_study_graph is None:
        _compiled_study_graph = build_study_graph()
    return _compiled_study_graph
