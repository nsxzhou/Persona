from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph


def build_novel_workflow_graph(*, state_type: type, pipeline: Any, checkpointer: Any):
    builder = StateGraph(state_type)
    builder.add_node("prepare_input", pipeline._prepare_input)
    builder.add_node("route_intent", pipeline._route_intent)
    builder.add_node("run_chapter_write", pipeline._run_chapter_write)
    builder.add_node("review_beats", pipeline._review_beats)
    builder.add_node("finalize_chapter_write", pipeline._finalize_chapter_write)
    builder.add_node("run_concept_bootstrap", pipeline._run_concept_bootstrap)
    builder.add_node("run_simple_intent", pipeline._run_simple_intent)

    builder.add_edge(START, "prepare_input")
    builder.add_edge("prepare_input", "route_intent")
    builder.add_conditional_edges(
        "route_intent",
        pipeline._select_intent_node,
        [
            "run_chapter_write",
            "run_concept_bootstrap",
            "run_simple_intent",
        ],
    )

    builder.add_edge("run_chapter_write", "review_beats")
    builder.add_edge("review_beats", "finalize_chapter_write")
    builder.add_edge("finalize_chapter_write", END)

    builder.add_edge("run_concept_bootstrap", END)
    builder.add_edge("run_simple_intent", END)
    return builder.compile(checkpointer=checkpointer)
