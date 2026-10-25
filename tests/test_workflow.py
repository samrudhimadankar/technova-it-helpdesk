"""TNH-16 Unit Testing: white-box tests for workflow.can_change_status.

CC = E - N + 2 = 13 - 10 + 2 = 5, so 5 independent paths (P1..P5, see Excel sheet 'White-Box').
"""
import pytest

import workflow as wf


@pytest.mark.parametrize("current, new, role, owner, assignee, expected, path", [
    ("Open", "Resolved", "admin", False, False, False, "P1 1-2-10 transition not in table"),
    ("Closed", "Open", "admin", True, True, False, "P1 1-2-10 closed is final"),
    ("Open", "In Progress", "admin", False, False, True, "P2 1-3-4-10 admin"),
    ("Open", "In Progress", "agent", False, True, True, "P4 1-3-5-6-8-10 assigned agent"),
    ("Open", "In Progress", "agent", False, False, False, "P4 1-3-5-6-8-10 agent not assigned"),
    ("In Progress", "Resolved", "employee", True, False, False, "P3 1-3-5-6-7-10 employee on staff move"),
    ("Resolved", "Closed", "employee", True, False, True, "P5 1-3-5-9-10 owner closes"),
    ("Resolved", "Closed", "agent", False, True, False, "P5 1-3-5-9-10 non-owner agent"),
    ("Resolved", "In Progress", "employee", True, False, True, "P5 1-3-5-9-10 owner reopens"),
    ("Open", "Closed", "employee", True, False, True, "P5 1-3-5-9-10 owner cancels"),
    ("Open", "Closed", "employee", False, False, False, "P5 1-3-5-9-10 non-owner employee"),
])
def test_can_change_status(current, new, role, owner, assignee, expected, path):
    assert wf.can_change_status(current, new, role, owner, assignee) is expected, path


def test_allowed_next_statuses():
    assert wf.allowed_next_statuses("Open", "admin", False, False) == ["In Progress", "Closed"]
    assert wf.allowed_next_statuses("Resolved", "employee", True, False) == ["Closed", "In Progress"]
    assert wf.allowed_next_statuses("Closed", "admin", True, True) == []


@pytest.mark.parametrize("role, status, ok", [
    ("admin", "Open", True), ("admin", "In Progress", True),
    ("admin", "Resolved", False), ("admin", "Closed", False),
    ("agent", "Open", False), ("employee", "Open", False),
])
def test_can_assign(role, status, ok):
    assert wf.can_assign(role, status) is ok
