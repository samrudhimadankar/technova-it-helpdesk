"""TNH-16 Unit Testing: white-box tests for validators.py.

Each validator is tested so that every branch (if / return) runs at least once,
plus boundary values (min-1, min, min+1, max-1, max, max+1).
"""
import pytest

import validators as v


# ---------- validate_password  (CC = E - N + 2 = 16 - 12 + 2 = 6, so 6 independent paths)

@pytest.mark.parametrize("pw, expected", [
    ("", "Password is required."),                              # P1  D1 true
    (None, "Password is required."),                            # P1  (None)
    ("abc123", "Password must be at least 8 characters."),      # P2  D2 true
    ("a1" * 11, "Password must be at most 20 characters."),     # P3  D3 true (22 chars)
    ("12345678", "Password must contain at least one letter."),  # P4  D4 true
    ("abcdefgh", "Password must contain at least one number."),  # P5  D5 true
    ("abcdefg1", None),                                         # P6  all false -> valid
])
def test_password_paths(pw, expected):
    assert v.validate_password(pw) == expected


@pytest.mark.parametrize("length, ok", [
    (7, False), (8, True), (9, True),      # lower boundary
    (19, True), (20, True), (21, False),   # upper boundary
])
def test_password_length_boundaries(length, ok):
    pw = "a1" + "x" * (length - 2)
    assert (v.validate_password(pw) is None) == ok


# ---------- validate_title (5..100 after trimming)

@pytest.mark.parametrize("length, ok", [
    (4, False), (5, True), (6, True), (99, True), (100, True), (101, False),
])
def test_title_boundaries(length, ok):
    assert (v.validate_title("t" * length) is None) == ok


def test_title_required_and_whitespace():
    assert v.validate_title("") == "Title is required."
    assert v.validate_title("     ") == "Title is required."
    assert v.validate_title(None) == "Title is required."
    # spaces around a short title should not push it over the minimum
    assert v.validate_title("  abc  ") is not None


# ---------- validate_description (10..1000)

@pytest.mark.parametrize("length, ok", [
    (9, False), (10, True), (11, True), (999, True), (1000, True), (1001, False),
])
def test_description_boundaries(length, ok):
    assert (v.validate_description("d" * length) is None) == ok


def test_description_required():
    assert v.validate_description("   ") == "Description is required."
    assert v.validate_description(None) == "Description is required."


# ---------- validate_name (2..50, letters and . ' - space)

@pytest.mark.parametrize("name, ok", [
    ("A", False), ("Al", True), ("A" * 50, True), ("A" * 51, False),
    ("Samrudhi Madankar", True), ("O'Brien", True), ("Mary-Jane", True),
    ("Sam123", False), ("Sam@", False), ("", False), ("   ", False), (None, False),
])
def test_name(name, ok):
    assert (v.validate_name(name) is None) == ok


# ---------- validate_email (equivalence classes)

@pytest.mark.parametrize("email, ok", [
    ("noah@technova.com", True),
    ("first.last+it@mail.co.in", True),
    ("noahtechnova.com", False),        # missing @
    ("noah@technova", False),           # missing domain extension
    ("@technova.com", False),           # missing local part
    ("noah@@technova.com", False),
    ("noah @technova.com", False),      # space
    ("", False), (None, False),
])
def test_email(email, ok):
    assert (v.validate_email(email) is None) == ok


# ---------- choices, notes, whole form

def test_choice():
    assert v.validate_choice("High", v.PRIORITIES, "priority") is None
    assert v.validate_choice("Urgent", v.PRIORITIES, "priority") == "Select a valid priority."
    assert v.validate_choice("", v.CATEGORIES, "category") == "Select a valid category."


@pytest.mark.parametrize("note, ok", [
    (None, False), ("", False), ("123456789", False), ("1234567890", True),
    ("   short   ", False),
])
def test_resolution_note(note, ok):
    assert (v.validate_resolution_note(note) is None) == ok


def test_validate_ticket_collects_all_errors():
    assert v.validate_ticket("Printer jam", "Printer on floor 2 is jammed", "Hardware", "Low") == []
    errors = v.validate_ticket("", "", "Food", "Urgent")
    assert len(errors) == 4
