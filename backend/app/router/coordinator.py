"""Stage A keyword router. Stage B (Haiku LLM-judge) is deferred per plan §5."""
from __future__ import annotations

import re

from app.models import RouteDecision

DAG_KEYWORDS: dict[str, str] = {
    r"\breset (my )?password\b": "password_reset",
    r"\b(?:unlock|unblock) (my )?account\b": "account_unlock",
    r"\b(?:i'?m|i am|account is|i got)\s+(locked out|locked|blocked)\b": "account_unlock",
    r"\breset (my )?(?:mfa|2fa|two[\s-]factor|multi[\s-]factor|authenticator)\b": "mfa_reset",
    r"\b(?:lost|new|broken|replaced) (my )?(?:phone|device|authenticator)\b.*\b(mfa|2fa|code)\b": "mfa_reset",
    r"\b(?:add(?:\s+me)?\s+to|join(?:\s+me)?(?:\s+to)?|grant(?:\s+me)?\s+access\s+to|subscribe\s+me\s+to|membership\s+in)\s+(?:the\s+)?(?:dl|distribution\s+list|mailing\s+list|email\s+group|google\s+group)\b": "distribution_list_access",
    r"\b(?:request|need|install|provision|grant me)\b(?:\s+\w+){0,4}?\s+(?:access|software|license|licence|app|application|tool|vpn)\b": "request_software",
}

HANDLED_DAG_INTENTS = {
    "password_reset",
    "account_unlock",
    "mfa_reset",
    "distribution_list_access",
    "request_software",
}


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
