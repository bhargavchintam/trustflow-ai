"""Tool registry. The Tool Gateway is the only legitimate consumer.

Adding a new tool requires:
1. Implementing it here or in a sibling module.
2. Registering it in TOOL_REGISTRY.
3. Adding a policy rule in app/policy/rules.py.
4. Adding at least one eval case in app/evals/synthetic_eval.json.

The policy-auditor agent enforces (1)-(3); the eval coverage check enforces (4).
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.models import Identity
from app.tools.check_vpn_status import check_vpn_status
from app.tools.file_ticket import file_ticket
from app.tools.reset_mfa import reset_mfa
from app.tools.reset_password import reset_password
from app.tools.unlock_account import unlock_account
from app.tools.vpn_diagnostic import vpn_diagnostic

ToolImpl = Callable[[dict[str, Any], Identity], Awaitable[dict[str, Any]]]

TOOL_REGISTRY: dict[str, ToolImpl] = {
    "vpn_diagnostic": vpn_diagnostic,
    "check_vpn_status": check_vpn_status,
    "reset_password": reset_password,
    "file_ticket": file_ticket,
    "unlock_account": unlock_account,
    "reset_mfa": reset_mfa,
}


def tool_names() -> list[str]:
    return sorted(TOOL_REGISTRY.keys())


def tool_descriptions() -> dict[str, str]:
    return {
        "vpn_diagnostic": (
            "Inspect the requester's VPN client. Returns client version, last disconnect, "
            "wake-event count, and a recommendation. Read-only. target_user must be self."
        ),
        "check_vpn_status": (
            "Get current VPN tunnel status for the requester (up/down, last handshake)."
        ),
        "reset_password": (
            "Initiate a password reset for the requester. Self-only; admin/executive "
            "requires HITL approval."
        ),
        "file_ticket": (
            "File a support ticket on behalf of the requester. Args: category (e.g. "
            "'software_request', 'hardware', 'access'), summary. Always allowed for self; "
            "use this when you can't resolve a problem yourself."
        ),
        "unlock_account": (
            "Unlock the requester's locked account after too many failed login attempts. "
            "Self-only."
        ),
        "reset_mfa": (
            "Reset the requester's multi-factor authentication enrolment so they can "
            "re-enrol on a new device. Self-only."
        ),
    }
