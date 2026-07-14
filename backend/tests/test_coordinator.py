"""Unit tests for router.coordinator.classify — the Stage A keyword router."""
from app.router.coordinator import classify


def test_password_reset_keyword():
    decision = classify("please reset my password")
    assert decision.route == "dag"
    assert decision.intent == "password_reset"
    assert decision.matched_by == "keyword"


def test_account_unlock_keyword():
    decision = classify("unlock my account")
    assert decision.route == "dag"
    assert decision.intent == "account_unlock"


def test_account_unlock_locked_out_phrasing():
    decision = classify("I'm locked out of everything")
    assert decision.route == "dag"
    assert decision.intent == "account_unlock"


def test_mfa_reset_keyword():
    decision = classify("reset my mfa please")
    assert decision.route == "dag"
    assert decision.intent == "mfa_reset"


def test_mfa_reset_lost_device_phrasing():
    decision = classify("lost my phone, need a new mfa code")
    assert decision.route == "dag"
    assert decision.intent == "mfa_reset"


def test_distribution_list_access_keyword():
    decision = classify("please add me to the distribution list")
    assert decision.route == "dag"
    assert decision.intent == "distribution_list_access"


def test_request_software_keyword():
    decision = classify("i need install access for figma desktop please")
    assert decision.route == "dag"
    assert decision.intent == "request_software"


def test_no_keyword_match_falls_back_to_react():
    decision = classify("my email is slow today")
    assert decision.route == "react"
    assert decision.intent is None
    assert decision.confidence == 0.0
    assert decision.matched_by == "fallback"


def test_request_software_regex_does_not_overmatch_unrelated_need():
    decision = classify("I need help understanding my invoice from last month")
    assert decision.route == "react"
    assert decision.intent is None


def test_force_route_react_overrides_keyword_match():
    decision = classify("reset my password", force_route="react")
    assert decision.route == "react"
    assert decision.intent is None
    assert decision.confidence == 1.0
    assert decision.matched_by == "forced"


def test_force_route_dag_overrides_no_match():
    decision = classify("my email is slow today", force_route="dag")
    assert decision.route == "dag"
    assert decision.intent == "forced"
    assert decision.confidence == 1.0
    assert decision.matched_by == "forced"
