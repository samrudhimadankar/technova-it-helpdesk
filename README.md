# TechNova IT Helpdesk

An IT support ticket system built for our Software Engineering PBL. Employees raise IT problems, the admin assigns them to support agents, agents fix and resolve them, and the employee closes the ticket.

**Live site:** https://samrudhi.pythonanywhere.com



## Features

- Register, login, profile, change password, logout
- 3 roles: **Employee**, **Agent** (IT support), **Admin**
- Raise tickets with category and priority, each gets a number like TKT-0001
- Search by keyword or ticket number, filter by status, priority and category
- Admin assigns tickets to agents, agents start work, change priority and comment
- Agent resolves with a resolution note, employee closes, reopens or cancels
- Ticket flow: **Open → In Progress → Resolved → Closed**
- Activity log on every ticket, input validation on every form

## Tech used

| Part | Tool |
| --- | --- |
| Backend | Python 3, Flask |
| Database | SQLite |
| Frontend | HTML (Jinja2 templates), CSS |
| Hosting | PythonAnywhere |
| Project management | Jira (3 sprints, 3 epics) |
| Testing | pytest + pytest-cov, Selenium + JUnit 5 (Maven) |

## Project structure

```
app.py               all routes (pages)
db.py                SQLite tables + demo data
validators.py        input rules (lengths, email, password ...)
workflow.py          who can move a ticket to which status
templates/           HTML pages
static/              CSS
tests/               pytest unit, integration and regression tests
automation-testing/  Maven project: Selenium black-box + JUnit white-box tests
docs/                test case workbook and screenshots
```

## Run it locally

```
python -m venv venv
venv\Scripts\activate          (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt -r requirements-dev.txt
python app.py
```
Open http://127.0.0.1:5000

### Demo accounts

| Role | Email | Password |
| --- | --- | --- |
| Admin | admin@technova.com | Admin@123 |
| Agent | christopher@technova.com | Agent@123 |
| Agent | emily@technova.com | Agent@123 |
| Employee | noah@technova.com | User@1234 |
| Employee | swara@technova.com | User@1234 |

## Testing

**Black-box**: 53 test cases in [docs/TechNova_Test_Cases.xlsx](docs/TechNova_Test_Cases.xlsx) using Equivalence Class Partitioning, Boundary Value Analysis and state transition testing. 4 bugs found on v1.0, all fixed in v1.1, 53/53 pass. Selenium script `automation-testing/.../First.java` runs 17 of these on the live site.

**White-box**: control flow graphs and cyclomatic complexity for `validate_password` (V(G) = 6) and `can_change_status` (V(G) = 5), one test per basis path.

```
pytest -v                     # 120 tests: 73 unit, 39 integration, 8 regression
pytest --cov=app --cov=validators --cov=workflow --cov=db --cov-branch --cov-report=term
```
Coverage: 97% overall, 100% for validators.py and workflow.py.

Java version (IntelliJ / Maven): open `automation-testing/`, run `Second` (white-box console), `TechNovaWhiteBoxTest` (JUnit) and `First` (Selenium on the live site).

## Jira

| Sprint | Dates | Epic | Stories |
| --- | --- | --- | --- |
| 1 | 4 to 11 Oct | TNH-2 User & Authentication | TNH-5 Registration & Login, TNH-7 Profile & Logout |
| 2 | 11 to 18 Oct | TNH-3 IT Support Ticket Management | TNH-11 Create & View, TNH-12 Assign & Update, TNH-13 Resolve & Close |
| 3 | 18 to 25 Oct | TNH-4 Testing & QA | TNH-14 + subtasks TNH-15 to TNH-19, 4 bugs |

---
Samrudhi Madankar · B.Tech CSE, Ramdeobaba University, Nagpur
