"""TNH-19 Bug Fix & Retest: one regression test per bug logged in Jira.
These failed on v1.0 and pass on v1.1.
"""
import pytest

import validators as v
from tests.conftest import ADMIN, EMP, login


def count(resp):
    import re
    return int(re.search(rb"(\d+) ticket\(s\) found", resp.data).group(1))


def test_bug01_percent_and_underscore_are_literal(client):
    login(client, *ADMIN)
    assert count(client.get("/tickets?q=%25")) == 0       # %
    assert count(client.get("/tickets?q=_")) == 0
    client.post("/tickets/new", data={"title": "Disk 100% full", "description": "C drive shows 100% used",
                                      "category": "Hardware", "priority": "High"})
    assert count(client.get("/tickets?q=100%25")) == 1


def test_bug02_number_search_includes_description(client):
    login(client, *EMP)
    client.post("/tickets/new", data={"title": "Intranet page broken",
                                      "description": "Intranet shows error 404 since today",
                                      "category": "Software", "priority": "Medium"})
    assert count(client.get("/tickets?q=404")) == 1
    assert count(client.get("/tickets?q=TKT-0001")) == 1  # ticket number search still works


def test_bug03_reopen_clears_old_resolution(client):
    login(client, *EMP)                                   # Noah owns resolved TKT-0003
    r = client.post("/tickets/3/status", data={"status": "In Progress"}, follow_redirects=True)
    assert b'class="pre resolution"' not in r.data


@pytest.mark.parametrize("length, ok", [(49, True), (50, True), (51, False), (5000, False)])
def test_bug04_department_max_50(length, ok):
    assert (v.validate_department("d" * length) is None) == ok


def test_bug04_profile_rejects_long_department(client):
    login(client, *EMP)
    r = client.post("/profile", data={"action": "details", "name": "Noah", "department": "x" * 5000},
                    follow_redirects=True)
    assert b"at most 50" in r.data
