"""Unit tests for policy.gateway.check_policy — the tenant/role decision logic."""
from app.models import Identity, ToolCall
from app.policy.gateway import check_policy

ALICE = Identity(tenant_id="acme", user_id="alice", session_id="s1", role="employee")
EXEC_BOB = Identity(tenant_id="acme", user_id="bob", session_id="s2", role="executive")
ADMIN_CARL = Identity(tenant_id="acme", user_id="carl", session_id="s3", role="admin")

HITL_TOOLS = ["reset_password", "unlock_account", "reset_mfa"]


def test_cross_user_target_denied():
    call = ToolCall(tool="reset_password", args={"target_user": "bob"})
    decision = check_policy(call, ALICE)
    assert decision.decision == "deny"
    assert "alice" in decision.reason
    assert "bob" in decision.reason


def test_self_target_allowed_for_employee():
    call = ToolCall(tool="reset_password", args={"target_user": "alice"})
    decision = check_policy(call, ALICE)
    assert decision.decision == "allow"


def test_self_target_defaults_when_target_user_omitted():
    call = ToolCall(tool="vpn_diagnostic", args={})
    decision = check_policy(call, ALICE)
    assert decision.decision == "allow"


def test_hitl_required_for_executive_and_admin_self_reset():
    for tool in HITL_TOOLS:
        for identity in (EXEC_BOB, ADMIN_CARL):
            call = ToolCall(tool=tool, args={"target_user": identity.user_id})
            decision = check_policy(call, identity)
            assert decision.decision == "hitl", f"{tool} for {identity.role} should require HITL"


def test_no_hitl_for_employee_self_reset():
    for tool in HITL_TOOLS:
        call = ToolCall(tool=tool, args={"target_user": "alice"})
        decision = check_policy(call, ALICE)
        assert decision.decision == "allow"


def test_cross_user_denied_even_for_admin():
    call = ToolCall(tool="reset_password", args={"target_user": "alice"})
    decision = check_policy(call, ADMIN_CARL)
    assert decision.decision == "deny"


def test_unregistered_tool_denied():
    call = ToolCall(tool="wipe_database", args={})
    decision = check_policy(call, ADMIN_CARL)
    assert decision.decision == "deny"
    assert "not registered" in decision.reason
