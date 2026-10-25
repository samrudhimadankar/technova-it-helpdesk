"""Ticket status workflow (who can move a ticket from one status to another).

Open -> In Progress -> Resolved -> Closed
Resolved -> In Progress   (requester reopens if the fix did not work)
Open -> Closed            (requester cancels their own ticket)
"""

STATUSES = ["Open", "In Progress", "Resolved", "Closed"]

# (from, to): who is allowed apart from admin
#   "staff" = the agent the ticket is assigned to
#   "owner" = the employee who raised the ticket
TRANSITIONS = {
    ("Open", "In Progress"): "staff",
    ("In Progress", "Resolved"): "staff",
    ("Resolved", "Closed"): "owner",
    ("Resolved", "In Progress"): "owner",
    ("Open", "Closed"): "owner",
}


def can_change_status(current, new, role, is_owner, is_assignee):
    who = TRANSITIONS.get((current, new))
    if who is None:
        return False
    if role == "admin":
        return True
    if who == "staff":
        return role == "agent" and is_assignee
    return is_owner


def allowed_next_statuses(current, role, is_owner, is_assignee):
    return [
        new for (cur, new) in TRANSITIONS
        if cur == current and can_change_status(current, new, role, is_owner, is_assignee)
    ]


def can_assign(role, status):
    """Only admin can assign / reassign, and only while the ticket is still being worked on."""
    return role == "admin" and status in ("Open", "In Progress")
