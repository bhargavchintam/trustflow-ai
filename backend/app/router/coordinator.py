"""Stage A keyword router. Stage B (Haiku LLM-judge) is deferred per plan §5."""
from __future__ import annotations

import re

from app.models import RouteDecision

DAG_KEYWORDS: dict[str, str] = {
    r"\breset (my )?password\b": "password_reset",
    r"\bunlock (my )?account\b": "account_unlock",
    r"\b(?:request|need|install|access to|provision|grant me)\s+\w": "request_software",
}

HANDLED_DAG_INTENTS = {"password_reset", "request_software"}


def classify(input_text: str, force_route: str | None = None) -> RouteDecision:
    if force_route == "react":
        return RouteDecision(route="react", intent=None, confidence=1.0, matched_by="forced")
    if force_route == "dag":
        return RouteDecision(
            route="dag", intent="forced", confidence=1.0, matched_by="forced"
        )

    lowered = input_text.lower()
    for pattern, intent in DAG_KEYWORDS.items():
        if re.search(pattern, lowered):
            if intent in HANDLED_DAG_INTENTS:
                return RouteDecision(
                    route="dag", intent=intent, confidence=0.95, matched_by="keyword"
                )
            return RouteDecision(
                route="react", intent=intent, confidence=0.0, matched_by="fallback"
            )

    return RouteDecision(route="react", intent=None, confidence=0.0, matched_by="fallback")
