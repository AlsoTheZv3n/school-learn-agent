"""Graph wiring (AG-1): route -> retrieve -> (assess -> update_model | explain) -> END.

DB/LLM deps are injected so the request-scoped session flows into the nodes. Note:
LangGraph's invoke returns a dict; run_turn reconstructs a typed TutorState.
"""

import dataclasses
from collections.abc import Callable

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from its.agent.nodes.assess import assess_node
from its.agent.nodes.explain import make_explain_node
from its.agent.nodes.retrieve import make_retrieve_node
from its.agent.nodes.route import route_node
from its.agent.nodes.update_model import make_update_model_node
from its.agent.state import Intent, TutorState
from its.llm.embeddings import Embedder


def build_graph(
    session: Session,
    *,
    embedder: Embedder | None = None,
    complete_fn: Callable[..., str] | None = None,
):
    g = StateGraph(TutorState)
    g.add_node("route", route_node)
    g.add_node("retrieve", make_retrieve_node(session, embedder))
    g.add_node("assess", assess_node)
    g.add_node("update_model", make_update_model_node(session))
    g.add_node("explain", make_explain_node(complete_fn))

    g.set_entry_point("route")
    g.add_edge("route", "retrieve")

    def branch(state) -> str:
        intent = state["intent"] if isinstance(state, dict) else state.intent
        return "assess" if intent == Intent.ANSWER else "explain"

    g.add_conditional_edges("retrieve", branch, {"assess": "assess", "explain": "explain"})
    g.add_edge("assess", "update_model")
    g.add_edge("update_model", END)
    g.add_edge("explain", END)
    return g.compile()


def run_turn(
    state: TutorState,
    *,
    session: Session,
    embedder: Embedder | None = None,
    complete_fn: Callable[..., str] | None = None,
) -> TutorState:
    """Run one turn and return a typed TutorState (LangGraph.invoke returns a dict)."""
    out = build_graph(session, embedder=embedder, complete_fn=complete_fn).invoke(state)
    names = {f.name for f in dataclasses.fields(TutorState)}
    return TutorState(**{k: v for k, v in out.items() if k in names})
