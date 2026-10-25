import os
from datetime import datetime, timedelta
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import db as database
import validators as v
import workflow as wf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IST = timedelta(hours=5, minutes=30)


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "change-this-secret-key"),
        DATABASE=os.path.join(BASE_DIR, "technova.db"),
    )
    if test_config:
        app.config.update(test_config)

    app.teardown_appcontext(database.close_db)
    with app.app_context():
        database.init_db(seed=app.config.get("SEED", True))

    register_filters(app)
    register_routes(app)
    return app


# ---------------------------------------------------------------- helpers

def register_filters(app):
    @app.template_filter("ist")
    def to_ist(value):
        """DB stores UTC, show Indian time on screen."""
        if not value:
            return "-"
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S") + IST
        return dt.strftime("%d %b %Y, %I:%M %p")

    @app.template_filter("tno")
    def ticket_no(ticket_id):
        return f"TKT-{ticket_id:04d}"


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in first.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if g.user["role"] not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def get_ticket_or_404(ticket_id):
    t = database.get_db().execute(
        """SELECT t.*, cu.name AS creator_name, cu.email AS creator_email,
                  au.name AS assignee_name
           FROM tickets t
           JOIN users cu ON cu.id = t.created_by
           LEFT JOIN users au ON au.id = t.assigned_to
           WHERE t.id = ?""", (ticket_id,)).fetchone()
    if t is None:
        abort(404)
    return t


def can_view(ticket, user):
    return (user["role"] == "admin" or ticket["created_by"] == user["id"]
            or ticket["assigned_to"] == user["id"])


def log_activity(ticket_id, action):
    database.get_db().execute(
        "INSERT INTO activity (ticket_id, user_id, action, created_at) VALUES (?,?,?,?)",
        (ticket_id, g.user["id"], action, database.now()))


# ---------------------------------------------------------------- routes

def register_routes(app):

    @app.before_request
    def load_user():
        uid = session.get("user_id")
        g.user = None
        if uid is not None:
            g.user = database.get_db().execute(
                "SELECT * FROM users WHERE id = ?", (uid,)).fetchone()

    @app.route("/")
    def index():
        return redirect(url_for("dashboard" if g.user else "login"))

    # ---------- TNH-5 User Registration & Login

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if g.user:
            return redirect(url_for("dashboard"))
        form = {}
        if request.method == "POST":
            form = request.form
            name = form.get("name", "").strip()
            email = form.get("email", "").strip().lower()
            password = form.get("password", "")
            confirm = form.get("confirm", "")
            errors = [e for e in (v.validate_name(name), v.validate_email(email),
                                  v.validate_password(password),
                                  v.validate_department(form.get("department", ""))) if e]
            if not errors and password != confirm:
                errors.append("Passwords do not match.")
            db = database.get_db()
            if not errors and db.execute("SELECT 1 FROM users WHERE email = ?",
                                         (email,)).fetchone():
                errors.append("An account with this email already exists.")
            if errors:
                for e in errors:
                    flash(e, "error")
                return render_template("register.html", form=form), 400
            db.execute(
                "INSERT INTO users (name, email, password_hash, role, department, created_at) "
                "VALUES (?, ?, ?, 'employee', ?, ?)",
                (name, email, generate_password_hash(password),
                 form.get("department", "").strip(), database.now()))
            db.commit()
            flash("Account created. You can log in now.", "success")
            return redirect(url_for("login"))
        return render_template("register.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if g.user:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            if not email or not password:
                flash("Email and password are required.", "error")
                return render_template("login.html", email=email), 400
            user = database.get_db().execute(
                "SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Invalid email or password.", "error")
                return render_template("login.html", email=email), 401
            session.clear()
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['name']}!", "success")
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//")
                            else url_for("dashboard"))
        return render_template("login.html", email="")

    # ---------- TNH-7 User Profile & Logout

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        flash("You have been logged out.", "success")
        return redirect(url_for("login"))

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        db = database.get_db()
        if request.method == "POST":
            action = request.form.get("action")
            if action == "details":
                name = request.form.get("name", "").strip()
                err = v.validate_name(name) or v.validate_department(
                    request.form.get("department", ""))
                if err:
                    flash(err, "error")
                else:
                    db.execute("UPDATE users SET name = ?, department = ? WHERE id = ?",
                               (name, request.form.get("department", "").strip(), g.user["id"]))
                    db.commit()
                    flash("Profile updated.", "success")
            elif action == "password":
                current = request.form.get("current", "")
                new = request.form.get("new", "")
                if not check_password_hash(g.user["password_hash"], current):
                    flash("Current password is wrong.", "error")
                elif v.validate_password(new):
                    flash(v.validate_password(new), "error")
                elif new != request.form.get("confirm", ""):
                    flash("New passwords do not match.", "error")
                else:
                    db.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                               (generate_password_hash(new), g.user["id"]))
                    db.commit()
                    flash("Password changed.", "success")
            return redirect(url_for("profile"))
        stats = db.execute(
            "SELECT COUNT(*) AS raised FROM tickets WHERE created_by = ?",
            (g.user["id"],)).fetchone()
        return render_template("profile.html", stats=stats)

    # ---------- Dashboard

    @app.route("/dashboard")
    @login_required
    def dashboard():
        where, params = scope_clause(g.user)
        db = database.get_db()
        counts = {s: 0 for s in wf.STATUSES}
        for row in db.execute(f"SELECT status, COUNT(*) c FROM tickets t WHERE {where} "
                              "GROUP BY status", params):
            counts[row["status"]] = row["c"]
        recent = db.execute(
            f"""SELECT t.*, au.name AS assignee_name FROM tickets t
                LEFT JOIN users au ON au.id = t.assigned_to
                WHERE {where} ORDER BY t.updated_at DESC, t.id DESC LIMIT 5""", params).fetchall()
        return render_template("dashboard.html", counts=counts, recent=recent,
                               total=sum(counts.values()))

    # ---------- TNH-11 Create & View Support Ticket

    @app.route("/tickets")
    @login_required
    def tickets():
        where, params = scope_clause(g.user)
        q = request.args.get("q", "").strip()
        status = request.args.get("status", "")
        priority = request.args.get("priority", "")
        category = request.args.get("category", "")
        sql = f"""SELECT t.*, cu.name AS creator_name, au.name AS assignee_name
                  FROM tickets t JOIN users cu ON cu.id = t.created_by
                  LEFT JOIN users au ON au.id = t.assigned_to WHERE {where}"""
        if q:
            # BUG-01 fix: escape % and _ so they are searched as normal characters
            like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            sql += " AND (t.title LIKE ? ESCAPE '\\' OR t.description LIKE ? ESCAPE '\\'"
            params += [like, like]
            # BUG-02 fix: a number now matches the ticket id AND still searches the description
            num = q.upper().replace("TKT-", "")
            if num.isdigit():
                sql += " OR t.id = ?"
                params.append(int(num))
            sql += ")"
        if status in wf.STATUSES:
            sql += " AND t.status = ?"
            params.append(status)
        if priority in v.PRIORITIES:
            sql += " AND t.priority = ?"
            params.append(priority)
        if category in v.CATEGORIES:
            sql += " AND t.category = ?"
            params.append(category)
        sql += " ORDER BY t.id DESC"
        rows = database.get_db().execute(sql, params).fetchall()
        return render_template("tickets.html", tickets=rows, q=q, status=status,
                               priority=priority, category=category,
                               statuses=wf.STATUSES, priorities=v.PRIORITIES,
                               categories=v.CATEGORIES)

    @app.route("/tickets/new", methods=["GET", "POST"])
    @login_required
    def new_ticket():
        form = {}
        if request.method == "POST":
            form = request.form
            title = form.get("title", "").strip()
            desc = form.get("description", "").strip()
            category = form.get("category", "")
            priority = form.get("priority", "")
            errors = v.validate_ticket(title, desc, category, priority)
            if errors:
                for e in errors:
                    flash(e, "error")
                return render_template("ticket_new.html", form=form,
                                       categories=v.CATEGORIES, priorities=v.PRIORITIES), 400
            db = database.get_db()
            ts = database.now()
            cur = db.execute(
                "INSERT INTO tickets (title, description, category, priority, status, created_by, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, 'Open', ?, ?, ?)",
                (title, desc, category, priority, g.user["id"], ts, ts))
            log_activity(cur.lastrowid, "Ticket created")
            db.commit()
            flash(f"Ticket TKT-{cur.lastrowid:04d} created.", "success")
            return redirect(url_for("ticket_detail", ticket_id=cur.lastrowid))
        return render_template("ticket_new.html", form=form,
                               categories=v.CATEGORIES, priorities=v.PRIORITIES)

    @app.route("/tickets/<int:ticket_id>")
    @login_required
    def ticket_detail(ticket_id):
        t = get_ticket_or_404(ticket_id)
        if not can_view(t, g.user):
            abort(403)
        db = database.get_db()
        comments = db.execute(
            "SELECT c.*, u.name, u.role FROM comments c JOIN users u ON u.id = c.user_id "
            "WHERE ticket_id = ? ORDER BY c.id", (ticket_id,)).fetchall()
        activity = db.execute(
            "SELECT a.*, u.name FROM activity a JOIN users u ON u.id = a.user_id "
            "WHERE ticket_id = ? ORDER BY a.id DESC", (ticket_id,)).fetchall()
        agents = db.execute("SELECT id, name FROM users WHERE role = 'agent' ORDER BY name"
                            ).fetchall()
        is_owner = t["created_by"] == g.user["id"]
        is_assignee = t["assigned_to"] == g.user["id"]
        next_statuses = wf.allowed_next_statuses(t["status"], g.user["role"], is_owner, is_assignee)
        return render_template(
            "ticket_detail.html", t=t, comments=comments, activity=activity, agents=agents,
            next_statuses=next_statuses, can_assign=wf.can_assign(g.user["role"], t["status"]),
            can_edit_priority=g.user["role"] in ("admin", "agent") and t["status"] != "Closed",
            priorities=v.PRIORITIES)

    # ---------- TNH-12 Assign & Update Ticket

    @app.route("/tickets/<int:ticket_id>/assign", methods=["POST"])
    @role_required("admin")
    def assign_ticket(ticket_id):
        t = get_ticket_or_404(ticket_id)
        if not wf.can_assign(g.user["role"], t["status"]):
            flash("This ticket can no longer be assigned.", "error")
            return redirect(url_for("ticket_detail", ticket_id=ticket_id))
        db = database.get_db()
        agent = db.execute("SELECT * FROM users WHERE id = ? AND role = 'agent'",
                           (request.form.get("agent_id", type=int),)).fetchone()
        if agent is None:
            flash("Select a valid support agent.", "error")
            return redirect(url_for("ticket_detail", ticket_id=ticket_id))
        db.execute("UPDATE tickets SET assigned_to = ?, updated_at = ? WHERE id = ?",
                   (agent["id"], database.now(), ticket_id))
        log_activity(ticket_id, f"Assigned to {agent['name']}")
        db.commit()
        flash(f"Ticket assigned to {agent['name']}.", "success")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))

    @app.route("/tickets/<int:ticket_id>/priority", methods=["POST"])
    @role_required("admin", "agent")
    def update_priority(ticket_id):
        t = get_ticket_or_404(ticket_id)
        if not can_view(t, g.user) or t["status"] == "Closed":
            abort(403)
        priority = request.form.get("priority", "")
        err = v.validate_choice(priority, v.PRIORITIES, "priority")
        if err:
            flash(err, "error")
        elif priority != t["priority"]:
            db = database.get_db()
            db.execute("UPDATE tickets SET priority = ?, updated_at = ? WHERE id = ?",
                       (priority, database.now(), ticket_id))
            log_activity(ticket_id, f"Priority changed {t['priority']} -> {priority}")
            db.commit()
            flash("Priority updated.", "success")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))

    # ---------- TNH-13 Resolve & Close Ticket (all status moves go here)

    @app.route("/tickets/<int:ticket_id>/status", methods=["POST"])
    @login_required
    def change_status(ticket_id):
        t = get_ticket_or_404(ticket_id)
        if not can_view(t, g.user):
            abort(403)
        new = request.form.get("status", "")
        is_owner = t["created_by"] == g.user["id"]
        is_assignee = t["assigned_to"] == g.user["id"]
        if not wf.can_change_status(t["status"], new, g.user["role"], is_owner, is_assignee):
            flash(f"You cannot move this ticket from {t['status']} to {new or 'nothing'}.", "error")
            return redirect(url_for("ticket_detail", ticket_id=ticket_id))
        if new == "In Progress" and t["assigned_to"] is None:
            flash("Assign the ticket to an agent first.", "error")
            return redirect(url_for("ticket_detail", ticket_id=ticket_id))

        db = database.get_db()
        ts = database.now()
        if new == "Resolved":
            note = request.form.get("note", "").strip()
            err = v.validate_resolution_note(note)
            if err:
                flash(err, "error")
                return redirect(url_for("ticket_detail", ticket_id=ticket_id))
            db.execute("UPDATE tickets SET status = ?, resolution_note = ?, updated_at = ? "
                       "WHERE id = ?", (new, note, ts, ticket_id))
        elif new == "Closed":
            db.execute("UPDATE tickets SET status = ?, closed_at = ?, updated_at = ? WHERE id = ?",
                       (new, ts, ts, ticket_id))
        elif t["status"] == "Resolved" and new == "In Progress":
            # BUG-03 fix: clear the old fix when the requester reopens, so it is not shown as the answer
            db.execute("UPDATE tickets SET status = ?, resolution_note = NULL, updated_at = ? "
                       "WHERE id = ?", (new, ts, ticket_id))
        else:
            db.execute("UPDATE tickets SET status = ?, updated_at = ? WHERE id = ?",
                       (new, ts, ticket_id))
        verb = "Reopened" if t["status"] == "Resolved" and new == "In Progress" else "Status"
        log_activity(ticket_id, f"{verb}: {t['status']} -> {new}")
        db.commit()
        flash(f"Ticket moved to {new}.", "success")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))

    @app.route("/tickets/<int:ticket_id>/comment", methods=["POST"])
    @login_required
    def add_comment(ticket_id):
        t = get_ticket_or_404(ticket_id)
        if not can_view(t, g.user):
            abort(403)
        body = request.form.get("body", "").strip()
        if not body:
            flash("Comment cannot be empty.", "error")
        elif len(body) > 500:
            flash("Comment must be at most 500 characters.", "error")
        elif t["status"] == "Closed":
            flash("Closed tickets cannot be commented on.", "error")
        else:
            db = database.get_db()
            db.execute("INSERT INTO comments (ticket_id, user_id, body, created_at) "
                       "VALUES (?,?,?,?)", (ticket_id, g.user["id"], body, database.now()))
            db.execute("UPDATE tickets SET updated_at = ? WHERE id = ?",
                       (database.now(), ticket_id))
            db.commit()
            flash("Comment added.", "success")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))

    # ---------- errors

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403,
                               message="You don't have permission to do that."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, message="Page not found."), 404


def scope_clause(user):
    """Which tickets a user is allowed to see."""
    if user["role"] == "admin":
        return "1=1", []
    if user["role"] == "agent":
        return "t.assigned_to = ?", [user["id"]]
    return "t.created_by = ?", [user["id"]]


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
