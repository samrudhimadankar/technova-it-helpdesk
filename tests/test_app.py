"""TNH-15 Functional / TNH-17 Integration testing through the Flask test client.

These run the real routes + real SQLite database together.
Seed data: TKT-0001 Open (Noah, unassigned), TKT-0002 In Progress (Swara -> Christopher),
TKT-0003 Resolved (Noah -> Emily).
"""
from tests.conftest import ADMIN, AGENT, AGENT2, EMP, EMP2, login


def new_ticket(client, **over):
    data = {"title": "Monitor flickering", "description": "Second monitor flickers every few seconds.",
            "category": "Hardware", "priority": "Medium"}
    data.update(over)
    return client.post("/tickets/new", data=data, follow_redirects=True)


# ------------------------------------------------ TNH-5 Registration & Login

class TestRegisterLogin:
    def test_register_then_login(self, client):
        r = client.post("/register", data={"name": "Riya Sharma", "email": "Riya@TechNova.com",
                                           "password": "Riya1234", "confirm": "Riya1234"},
                        follow_redirects=True)
        assert b"Account created" in r.data
        r = login(client, "riya@technova.com", "Riya1234")       # email saved in lowercase
        assert r.status_code == 302 and r.headers["Location"].endswith("/dashboard")

    def test_register_duplicate_email(self, client):
        r = client.post("/register", data={"name": "Noah Two", "email": "NOAH@technova.com",
                                           "password": "Noah1234", "confirm": "Noah1234"})
        assert r.status_code == 400 and b"already exists" in r.data

    def test_register_password_mismatch(self, client):
        r = client.post("/register", data={"name": "Riya", "email": "riya@x.com",
                                           "password": "Riya1234", "confirm": "Riya12345"})
        assert r.status_code == 400 and b"do not match" in r.data

    def test_register_invalid_inputs(self, client):
        r = client.post("/register", data={"name": "R", "email": "bad", "password": "short",
                                           "confirm": "short"})
        assert r.status_code == 400
        assert b"Name must be" in r.data and b"valid email" in r.data and b"at least 8" in r.data

    def test_login_wrong_password(self, client):
        r = login(client, ADMIN[0], "Wrong123")
        assert r.status_code == 401 and b"Invalid email or password" in r.data

    def test_login_unknown_email(self, client):
        assert login(client, "ghost@technova.com", "Ghost123").status_code == 401

    def test_login_empty_fields(self, client):
        r = login(client, "", "")
        assert r.status_code == 400 and b"required" in r.data

    def test_protected_page_redirects_to_login(self, client):
        r = client.get("/tickets")
        assert r.status_code == 302 and "/login" in r.headers["Location"]

    def test_login_redirects_back_to_next(self, client):
        r = client.post("/login?next=/tickets/new", data={"email": EMP[0], "password": EMP[1]})
        assert r.headers["Location"].endswith("/tickets/new")

    def test_login_ignores_external_next(self, client):
        r = client.post("/login?next=//evil.com", data={"email": EMP[0], "password": EMP[1]})
        assert r.headers["Location"].endswith("/dashboard")


# ------------------------------------------------ TNH-7 Profile & Logout

class TestProfileLogout:
    def test_logout_clears_session(self, client):
        login(client, *EMP)
        client.post("/logout")
        assert client.get("/dashboard").status_code == 302

    def test_update_profile(self, client):
        login(client, *EMP)
        r = client.post("/profile", data={"action": "details", "name": "Noah Fernandes",
                                          "department": "Accounts"}, follow_redirects=True)
        assert b"Profile updated" in r.data and b"Noah Fernandes" in r.data

    def test_update_profile_invalid_name(self, client):
        login(client, *EMP)
        r = client.post("/profile", data={"action": "details", "name": "N0ah"},
                        follow_redirects=True)
        assert b"Name can only contain" in r.data

    def test_change_password_flow(self, client):
        login(client, *EMP)
        r = client.post("/profile", data={"action": "password", "current": "User@1234",
                                          "new": "NewPass99", "confirm": "NewPass99"},
                        follow_redirects=True)
        assert b"Password changed" in r.data
        client.post("/logout")
        assert login(client, EMP[0], "User@1234").status_code == 401
        assert login(client, EMP[0], "NewPass99").status_code == 302

    def test_change_password_wrong_current(self, client):
        login(client, *EMP)
        r = client.post("/profile", data={"action": "password", "current": "nope",
                                          "new": "NewPass99", "confirm": "NewPass99"},
                        follow_redirects=True)
        assert b"Current password is wrong" in r.data

    def test_change_password_weak_or_mismatch(self, client):
        login(client, *EMP)
        r = client.post("/profile", data={"action": "password", "current": "User@1234",
                                          "new": "weak", "confirm": "weak"}, follow_redirects=True)
        assert b"at least 8" in r.data
        r = client.post("/profile", data={"action": "password", "current": "User@1234",
                                          "new": "NewPass99", "confirm": "NewPass98"},
                        follow_redirects=True)
        assert b"do not match" in r.data


# ------------------------------------------------ TNH-11 Create & View Ticket

class TestCreateView:
    def test_create_ticket(self, client):
        login(client, *EMP)
        r = new_ticket(client)
        assert b"TKT-0004 created" in r.data and b"Open" in r.data and b"Unassigned" in r.data

    def test_create_ticket_validation(self, client):
        login(client, *EMP)
        r = new_ticket(client, title="abc", description="short", category="", priority="")
        assert r.status_code == 400
        for msg in (b"Title must be", b"Description must be", b"valid category", b"valid priority"):
            assert msg in r.data

    def test_employee_sees_only_own_tickets(self, client):
        login(client, *EMP)                      # Noah owns 1 and 3
        r = client.get("/tickets")
        assert b'href="/tickets/1"' in r.data and b'href="/tickets/3"' in r.data
        assert b'href="/tickets/2"' not in r.data
        assert client.get("/tickets/2").status_code == 403

    def test_agent_sees_only_assigned(self, client):
        login(client, *AGENT)                    # Christopher has 2
        r = client.get("/tickets")
        assert b'href="/tickets/2"' in r.data and b'href="/tickets/1"' not in r.data

    def test_admin_sees_all(self, client):
        login(client, *ADMIN)
        r = client.get("/tickets")
        assert b"3 ticket(s) found" in r.data

    def test_search_and_filters(self, client):
        login(client, *ADMIN)
        assert b"1 ticket(s) found" in client.get("/tickets?q=vpn").data
        assert b"1 ticket(s) found" in client.get("/tickets?q=TKT-0003").data
        assert b"1 ticket(s) found" in client.get("/tickets?status=Open").data
        assert b"1 ticket(s) found" in client.get("/tickets?priority=High").data
        assert b"1 ticket(s) found" in client.get("/tickets?category=Network").data
        assert b"0 ticket(s) found" in client.get("/tickets?q=zzzz").data
        # unknown filter value is ignored instead of crashing
        assert b"3 ticket(s) found" in client.get("/tickets?status=Banana").data

    def test_missing_ticket_404(self, client):
        login(client, *ADMIN)
        assert client.get("/tickets/999").status_code == 404


# ------------------------------------------------ TNH-12 Assign & Update

class TestAssignUpdate:
    def test_admin_assigns_ticket(self, client):
        login(client, *ADMIN)
        r = client.post("/tickets/1/assign", data={"agent_id": 3}, follow_redirects=True)
        assert b"Ticket assigned to Emily" in r.data

    def test_assign_to_non_agent_rejected(self, client):
        login(client, *ADMIN)
        r = client.post("/tickets/1/assign", data={"agent_id": 4}, follow_redirects=True)
        assert b"valid support agent" in r.data

    def test_employee_and_agent_cannot_assign(self, client):
        login(client, *EMP)
        assert client.post("/tickets/1/assign", data={"agent_id": 2}).status_code == 403
        client.post("/logout")
        login(client, *AGENT)
        assert client.post("/tickets/1/assign", data={"agent_id": 2}).status_code == 403

    def test_cannot_assign_resolved_ticket(self, client):
        login(client, *ADMIN)
        r = client.post("/tickets/3/assign", data={"agent_id": 2}, follow_redirects=True)
        assert b"can no longer be assigned" in r.data

    def test_start_work_needs_assignee(self, client):
        login(client, *ADMIN)
        r = client.post("/tickets/1/status", data={"status": "In Progress"}, follow_redirects=True)
        assert b"Assign the ticket to an agent first" in r.data

    def test_agent_changes_priority(self, client):
        login(client, *AGENT)
        r = client.post("/tickets/2/priority", data={"priority": "Critical"}, follow_redirects=True)
        assert b"Priority updated" in r.data and b"Medium -&gt; Critical" in r.data

    def test_invalid_priority(self, client):
        login(client, *AGENT)
        r = client.post("/tickets/2/priority", data={"priority": "Urgent"}, follow_redirects=True)
        assert b"valid priority" in r.data

    def test_employee_cannot_change_priority(self, client):
        login(client, *EMP2)
        assert client.post("/tickets/2/priority", data={"priority": "Low"}).status_code == 403

    def test_comment(self, client):
        login(client, *EMP2)
        r = client.post("/tickets/2/comment", data={"body": "Still dropping today"},
                        follow_redirects=True)
        assert b"Comment added" in r.data and b"Still dropping today" in r.data
        r = client.post("/tickets/2/comment", data={"body": "   "}, follow_redirects=True)
        assert b"cannot be empty" in r.data
        r = client.post("/tickets/2/comment", data={"body": "x" * 501}, follow_redirects=True)
        assert b"at most 500" in r.data


# ------------------------------------------------ TNH-13 Resolve & Close (full lifecycle)

class TestResolveClose:
    def test_full_lifecycle(self, client):
        # employee raises
        login(client, *EMP)
        new_ticket(client, title="Outlook not syncing")
        client.post("/logout")
        # admin assigns to Christopher
        login(client, *ADMIN)
        client.post("/tickets/4/assign", data={"agent_id": 2})
        client.post("/logout")
        # agent starts and resolves
        login(client, *AGENT)
        client.post("/tickets/4/status", data={"status": "In Progress"})
        r = client.post("/tickets/4/status", data={"status": "Resolved",
                                                   "note": "Recreated the Outlook profile."},
                        follow_redirects=True)
        assert b"Ticket moved to Resolved" in r.data
        client.post("/logout")
        # employee closes
        login(client, *EMP)
        r = client.post("/tickets/4/status", data={"status": "Closed"}, follow_redirects=True)
        assert b"Ticket moved to Closed" in r.data and b"Recreated the Outlook profile" in r.data
        # closed is final
        r = client.post("/tickets/4/status", data={"status": "In Progress"}, follow_redirects=True)
        assert b"You cannot move this ticket" in r.data
        r = client.post("/tickets/4/comment", data={"body": "thanks"}, follow_redirects=True)
        assert b"Closed tickets cannot be commented on" in r.data

    def test_resolve_needs_note(self, client):
        login(client, *AGENT)
        r = client.post("/tickets/2/status", data={"status": "Resolved", "note": "fixed"},
                        follow_redirects=True)
        assert b"at least 10 characters" in r.data

    def test_other_agent_cannot_resolve(self, client):
        login(client, *AGENT2)                   # Emily, but ticket 2 is Christopher's
        assert client.post("/tickets/2/status", data={"status": "Resolved",
                                                      "note": "Not my ticket"}).status_code == 403

    def test_owner_reopens_resolved(self, client):
        login(client, *EMP)
        r = client.post("/tickets/3/status", data={"status": "In Progress"}, follow_redirects=True)
        assert b"Reopened: Resolved -&gt; In Progress" in r.data

    def test_owner_cancels_open(self, client):
        login(client, *EMP)
        r = client.post("/tickets/1/status", data={"status": "Closed"}, follow_redirects=True)
        assert b"Ticket moved to Closed" in r.data

    def test_skip_status_not_allowed(self, client):
        login(client, *ADMIN)
        r = client.post("/tickets/1/status", data={"status": "Resolved", "note": "skip skip skip"},
                        follow_redirects=True)
        assert b"You cannot move this ticket" in r.data

    def test_dashboard_counts(self, client):
        login(client, *ADMIN)
        r = client.get("/dashboard")
        assert r.status_code == 200 and b"Recently updated" in r.data
