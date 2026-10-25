"""Input validation rules for TechNova IT Helpdesk.

Every function returns None when the input is valid,
or a short error message (string) when it is not.
These are kept as plain functions so they are easy to unit test.
"""
import re

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

CATEGORIES = ["Hardware", "Software", "Network", "Account / Access", "Other"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]

NAME_MIN, NAME_MAX = 2, 50
PASSWORD_MIN, PASSWORD_MAX = 8, 20
TITLE_MIN, TITLE_MAX = 5, 100
DESC_MIN, DESC_MAX = 10, 1000
NOTE_MIN = 10
DEPT_MAX = 50


def validate_name(name):
    if name is None or name.strip() == "":
        return "Name is required."
    name = name.strip()
    if len(name) < NAME_MIN or len(name) > NAME_MAX:
        return f"Name must be {NAME_MIN} to {NAME_MAX} characters."
    if not all(ch.isalpha() or ch in " .'-" for ch in name):
        return "Name can only contain letters, spaces, dots, hyphens and apostrophes."
    return None


def validate_department(department):
    # BUG-04 fix: department had no length check at all
    if department and len(department.strip()) > DEPT_MAX:
        return f"Department must be at most {DEPT_MAX} characters."
    return None


def validate_email(email):
    if email is None or email.strip() == "":
        return "Email is required."
    if not EMAIL_PATTERN.match(email.strip()):
        return "Enter a valid email address."
    return None


def validate_password(password):
    if not password:
        return "Password is required."
    if len(password) < PASSWORD_MIN:
        return f"Password must be at least {PASSWORD_MIN} characters."
    if len(password) > PASSWORD_MAX:
        return f"Password must be at most {PASSWORD_MAX} characters."
    if not any(ch.isalpha() for ch in password):
        return "Password must contain at least one letter."
    if not any(ch.isdigit() for ch in password):
        return "Password must contain at least one number."
    return None


def validate_title(title):
    if title is None or title.strip() == "":
        return "Title is required."
    length = len(title.strip())
    if length < TITLE_MIN:
        return f"Title must be at least {TITLE_MIN} characters."
    if length > TITLE_MAX:
        return f"Title must be at most {TITLE_MAX} characters."
    return None


def validate_description(description):
    if description is None or description.strip() == "":
        return "Description is required."
    length = len(description.strip())
    if length < DESC_MIN:
        return f"Description must be at least {DESC_MIN} characters."
    if length > DESC_MAX:
        return f"Description must be at most {DESC_MAX} characters."
    return None


def validate_choice(value, options, field):
    if value not in options:
        return f"Select a valid {field}."
    return None


def validate_resolution_note(note):
    if note is None or len(note.strip()) < NOTE_MIN:
        return f"Resolution note must be at least {NOTE_MIN} characters."
    return None


def validate_ticket(title, description, category, priority):
    """Validate the whole create-ticket form. Returns a list of errors."""
    errors = []
    for err in (
        validate_title(title),
        validate_description(description),
        validate_choice(category, CATEGORIES, "category"),
        validate_choice(priority, PRIORITIES, "priority"),
    ):
        if err:
            errors.append(err)
    return errors
