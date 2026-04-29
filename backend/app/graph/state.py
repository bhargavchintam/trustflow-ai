from typing import Any, TypedDict

from app.models import Identity


class GraphState(TypedDict, total=False):
    identity: Identity
    correlation_id: str
    message_id: str
    user_input: str
    iteration: int
    max_iterations: int
    prompt_tokens: int
    completion_tokens: int
    max_tokens: int

    episodic_hits: list[dict[str, Any]]
    semantic_hits: list[dict[str, Any]]
    procedural_hits: list[dict[str, Any]]
    procedural_used: bool

    proposed_tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]

    final_response: str
    blocked: bool
