import sqlite3
from datetime import datetime, timezone

from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'employee',      -- employee / agent / admin
    department TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Open',
    created_by INTEGER NOT NULL REFERENCES users(id),
    assigned_to INTEGER REFERENCES users(id),
    resolution_note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    action TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

# Demo accounts (same people as the Jira team so the demo lines up)
DEMO_USERS = [
    ("Samrudhi Madankar", "admin@technova.com", "Admin@123", "admin", "IT Department"),
    ("Christopher", "christopher@technova.com", "Agent@123", "agent", "IT Support"),
    ("Emily", "emily@technova.com", "Agent@123", "agent", "IT Support"),
    ("Noah", "noah@technova.com", "User@1234", "employee", "Finance"),
    ("Swara Madankar", "swara@technova.com", "User@1234", "employee", "HR"),
]


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(seed=True):
    db = get_db()
    db.executescript(SCHEMA)
    if seed and db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        for name, email, pw, role, dept in DEMO_USERS:
            db.execute(
                "INSERT INTO users (name, email, password_hash, role, department, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (name, email, generate_password_hash(pw), role, dept, now()),
            )
        _seed_tickets(db)
    db.commit()


def _seed_tickets(db):
    ids = {r["email"]: r["id"] for r in db.execute("SELECT id, email FROM users")}
    samples = [
        ("Laptop not turning on", "My office laptop does not power on even after charging overnight.",
         "Hardware", "High", "Open", "noah@technova.com", None),
        ("VPN keeps disconnecting", "VPN drops every 10 minutes when working from home, need a fix.",
         "Network", "Medium", "In Progress", "swara@technova.com", "christopher@technova.com"),
        ("Need access to payroll portal", "Please give me read access to the payroll portal for audit work.",
         "Account / Access", "Low", "Resolved", "noah@technova.com", "emily@technova.com"),
    ]
    for title, desc, cat, pri, status, by, to in samples:
        ts = now()
        cur = db.execute(
            "INSERT INTO tickets (title, description, category, priority, status, created_by, "
            "assigned_to, resolution_note, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (title, desc, cat, pri, status, ids[by], ids.get(to),
             "Access granted by IT admin." if status == "Resolved" else None, ts, ts),
        )
        db.execute(
            "INSERT INTO activity (ticket_id, user_id, action, created_at) VALUES (?,?,?,?)",
            (cur.lastrowid, ids[by], "Ticket created", ts),
        )
