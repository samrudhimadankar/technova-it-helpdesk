import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402


@pytest.fixture
def app(tmp_path):
    """Fresh app + fresh SQLite file for every test (demo users and 3 sample tickets)."""
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db"),
                       "SECRET_KEY": "test"})


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, password):
    return client.post("/login", data={"email": email, "password": password})


ADMIN = ("admin@technova.com", "Admin@123")
AGENT = ("christopher@technova.com", "Agent@123")     # agent id 2
AGENT2 = ("emily@technova.com", "Agent@123")         # agent id 3
EMP = ("noah@technova.com", "User@1234")             # employee id 4
EMP2 = ("swara@technova.com", "User@1234")           # employee id 5
