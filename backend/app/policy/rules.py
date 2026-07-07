"""Policy rules per tool. The Tool Gateway reads from this.

Each rule:
- max_target_user: "self" means tool can only be invoked with target_user == requester.
                   "any" means no target restriction.
                   list[str] means an allowlist of specific target users.
- requires_hitl_for: list of roles where the tool requires human approval.
"""
from typing import Any, Literal, TypedDict

ALLOWED_ROLES = ["employee", "executive", "admin"]


class PolicyRule(TypedDict, total=False):
    max_target_user: Literal["self", "any"] | list[str]
    requires_hitl_for: list[str]
    description: str


POLICY_RULES: dict[str, PolicyRule] = {
    "reset_password": {
        "max_target_user": "self",
        "requires_hitl_for": ["executive", "admin"],
        "description": "Reset the requester's own password. Cross-user is denied; "
                       "executive/admin self-reset requires approval.",
    },
    "vpn_diagnostic": {
        "max_target_user": "self",
        "requires_hitl_for": [],
        "description": "Inspect the requester's VPN client state. Read-only, self-only.",
    },
    "check_vpn_status": {
        "max_target_user": "self",
        "requires_hitl_for": [],
        "description": "Read VPN tunnel status for the requester.",
    },
    "file_ticket": {
        "max_target_user": "self",
        "requires_hitl_for": [],
        "description": "File a support ticket. Always self-targeted; never escalates.",
    },
    "unlock_account": {
        "max_target_user": "self",
        "requires_hitl_for": ["executive", "admin"],
        "description": "Unlock the requester's locked account. Self-only; admin/executive "
                       "requires approval.",
    },
    "reset_mfa": {
        "max_target_user": "self",
        "requires_hitl_for": ["executive", "admin"],
        "description": "Reset the requester's MFA enrolment. Self-only; admin/executive "
                       "requires approval.",
    },
}


def deny_reason(tool: str, args: dict[str, Any], identity_user: str, role: str) -> str:
    """Produce a human-readable deny reason for logs and UI."""
    target = args.get("target_user", identity_user)
    return (
        f"Cross-user {tool} blocked: target={target}, requester={identity_user}, role={role}"
    )
