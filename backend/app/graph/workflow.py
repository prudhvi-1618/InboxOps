from langgraph.graph import StateGraph, END
from app.graph.state import EmailProcessingState
from app.graph.nodes.preprocess import preprocess_node
from app.graph.nodes.hygiene import hygiene_node
from app.graph.nodes.classify import classify_node
from app.graph.nodes.extract import extract_node
from app.graph.nodes.route import route_node
from app.graph.nodes.priority import priority_node
from app.graph.nodes.task_writer import task_writer_node
from app.core.logging import get_logger

logger = get_logger(__name__)


def should_skip(state: EmailProcessingState) -> str:
    """Edge condition: skip if already decided to skip or already processed."""
    if state.get("already_processed"):
        return "done"
    if state.get("skip"):
        return "done"
    return "classify"


def should_write(state: EmailProcessingState) -> str:
    """Edge condition: skip task write if Gemini failed or email was skipped."""
    if state.get("decision") == "error":
        return "done"
    if state.get("skip"):
        return "done"
    return "task_writer"


def build_graph() -> StateGraph:
    graph = StateGraph(EmailProcessingState)

    graph.add_node("preprocess",  preprocess_node)
    graph.add_node("hygiene",     hygiene_node)
    graph.add_node("classify",    classify_node)
    graph.add_node("extract",     extract_node)
    graph.add_node("route",       route_node)
    graph.add_node("priority",    priority_node)
    graph.add_node("task_writer", task_writer_node)

    graph.set_entry_point("preprocess")

    graph.add_edge("preprocess", "hygiene")

    graph.add_conditional_edges(
        "hygiene",
        should_skip,
        {
            "done": END,
            "classify": "classify",
        },
    )

    graph.add_edge("classify", "extract")
    graph.add_edge("extract", "route")
    graph.add_edge("route", "priority")

    graph.add_conditional_edges(
        "priority",
        should_write,
        {
            "done": END,
            "task_writer": "task_writer",
        },
    )

    graph.add_edge("task_writer", END)

    return graph


compiled_graph = build_graph().compile()
email_graph = compiled_graph
