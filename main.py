from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, text
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a-very-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)

# ----------------- MODELS -----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(60), nullable=False)

    notes = db.relationship('Note', backref='author', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'date_created': self.date_created.isoformat()
        }

    def __repr__(self):
        return f"Note('{self.title}', '{self.date_created}')"


class Workspace(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


User.workspaces = db.relationship(
    'Workspace', backref='owner', lazy=True, cascade="all, delete-orphan"
)


class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    user = db.relationship('User')


# ---- task status helpers / model ----
STATUS_CHOICES = {"todo", "in_progress", "done"}


def canonical_status(value: str | None) -> str | None:
    """Map many possible inputs to our canonical values: todo / in_progress / done."""
    s = (value or "").strip().lower()
    if s in ("todo", "to do", "to_do"):
        return "todo"
    if s in ("in progress", "in_progress", "inprogress"):
        return "in_progress"
    if s in ("done", "complete", "completed"):
        return "done"
    return None


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    # persisted canonical status
    status = db.Column(db.String(20), nullable=False, default="todo")
    # keep old flag for compatibility (kept in sync)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# -------------- AUTH DECORATOR --------------
def login_required_page(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ----------------- PAGES -----------------
@app.route("/tasks")
@login_required_page
def tasks_page():
    user = User.query.get(session['user_id'])
    return render_template("task.html", user=user)


# Keep /task as an alias to /tasks
@app.route("/task")
@login_required_page
def task_page_alias():
    return redirect(url_for("tasks_page"))


@app.route('/')
def home():
    return render_template("home.html")


@app.route('/register', methods=['GET'])
def register_page():
    return render_template("register.html")


# ----------------- AUTH API -----------------
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')

    if not all([name, username, email, password, confirm_password]):
        return jsonify({'status': 'error', 'message': 'All fields are required.'}), 400

    if len(password) < 5:
        return jsonify({
            'status': 'error',
            'errors': {'password': 'Password must be at least 5 characters long.'}
        }), 400

    if password != confirm_password:
        return jsonify({'status': 'error', 'message': 'Passwords do not match.'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'status': 'error', 'message': 'Username already exists.'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'status': 'error', 'message': 'Email already registered.'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    new_user = User(
        name=name,
        username=username,
        email=email,
        password_hash=hashed_password
    )

    db.session.add(new_user)
    db.session.commit()

    print(f"User '{username}' successfully registered and stored in database.")
    return jsonify({'status': 'success', 'message': 'Registration successful!'}), 201


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'GET':
        return render_template("login.html")

    data = request.get_json()
    login_identifier = data.get('login_identifier')
    password = data.get('password')

    if not login_identifier or not password:
        return jsonify({'status': 'error', 'message': 'Username/Email and password are required.'}), 400

    user = User.query.filter(
        or_(User.username == login_identifier, User.email == login_identifier)
    ).first()

    if user and bcrypt.check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        print(f"User '{user.username}' logged in successfully.")
        return jsonify({'status': 'success', 'message': 'Login successful!'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Invalid credentials.'}), 401


@app.route("/dashboard")
@login_required_page
def dashboard():
    user = User.query.get(session['user_id'])
    return render_template("dashboard.html", user=user)


@app.route("/profile")
@login_required_page
def profile():
    user = User.query.get(session['user_id'])
    return render_template("profile.html", user=user)


@app.route("/profile/edit", methods=["GET"])
@login_required_page
def edit_profile_page():
    user = User.query.get_or_404(session["user_id"])
    return render_template("edit_profile.html", user=user)


@csrf.exempt
@app.route("/api/profile/basic", methods=["POST"])
@login_required_page
def api_update_profile_basic():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()

    if not all([name, username, email]):
        return jsonify({"status": "error", "message": "All fields are required."}), 400

    user = User.query.get(session["user_id"])
    if not user:
        session.clear()
        return jsonify({"status": "error", "message": "Not authenticated."}), 401

    if User.query.filter(User.username == username, User.id != user.id).first():
        return jsonify({"status": "error", "field": "username", "message": "Username already in use."}), 400

    if User.query.filter(User.email == email, User.id != user.id).first():
        return jsonify({"status": "error", "field": "email", "message": "Email already in use."}), 400

    user.name = name
    user.username = username
    user.email = email
    db.session.commit()

    return jsonify({"status": "success"}), 200


# ----------------- TASKS API -----------------
@csrf.exempt
@app.route("/api/tasks", methods=["GET"])
@login_required_page
def list_tasks():
    user_id = session["user_id"]
    # optional filter: accepts 'todo', 'in_progress', 'done' or the older labels
    raw = request.args.get("status")
    st = canonical_status(raw)
    q = Task.query.filter_by(user_id=user_id)
    if st in STATUS_CHOICES:
        q = q.filter(Task.status == st)
    tasks = q.order_by(Task.created_at.desc()).all()

    def to_dict(t):
        return {
            "id": t.id,
            "title": t.title,
            "description": t.description or "",
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "status": t.status,
            "completed": bool(t.completed),
            "created_at": t.created_at.isoformat()
        }
    return jsonify([to_dict(t) for t in tasks]), 200


@csrf.exempt
@app.route("/api/tasks", methods=["POST"])
@login_required_page
def create_task():
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    due_date_str = (data.get("due_date") or "").strip()
    status = canonical_status(data.get("status"))  # may be None

    if not title:
        return jsonify({"status": "error", "message": "Title is required."}), 400

    if status not in STATUS_CHOICES:
        # back-compat: derive from completed flag; else default todo
        status = "done" if bool(data.get("completed")) else "todo"

    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid date format. Use YYYY-MM-DD."}), 400

    task = Task(
        title=title,
        description=description or None,
        due_date=due_date,
        status=status,
        completed=(status == "done"),
        user_id=session["user_id"],
    )
    db.session.add(task)
    db.session.commit()
    return jsonify({"id": task.id}), 201


@csrf.exempt
@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
@login_required_page
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != session["user_id"]:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    data = request.get_json() or {}

    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"status": "error", "message": "Title is required."}), 400
        task.title = title

    if "description" in data:
        desc = (data.get("description") or "").strip()
        task.description = desc or None

    if "due_date" in data:
        dd = (data.get("due_date") or "").strip()
        if dd:
            try:
                task.due_date = datetime.strptime(dd, "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid date format. Use YYYY-MM-DD."}), 400
        else:
            task.due_date = None

    if "status" in data:
        st = canonical_status(data.get("status"))
        if st not in STATUS_CHOICES:
            return jsonify({"status": "error", "message": "Invalid status."}), 400
        task.status = st
        task.completed = (st == "done")

    # back-compat: allow toggling 'completed' alone
    if "completed" in data and "status" not in data:
        comp = bool(data.get("completed"))
        task.completed = comp
        task.status = "done" if comp else "todo"

    db.session.commit()
    return jsonify({"status": "success"}), 200


@csrf.exempt
@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
@login_required_page
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != session["user_id"]:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    db.session.delete(task)
    db.session.commit()
    return jsonify({"status": "success"}), 200


# --- Bulk delete tasks (selected in UI)
@csrf.exempt
@app.route("/api/tasks/bulk_delete", methods=["POST"])
@login_required_page
def bulk_delete_tasks():
    data = request.get_json() or {}
    ids = data.get("ids") or []
    if not isinstance(ids, list) or not ids:
        return jsonify({"status": "error", "message": "No task ids provided."}), 400

    q = Task.query.filter(Task.user_id == session["user_id"], Task.id.in_(ids))
    deleted = q.delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"status": "success", "deleted": deleted}), 200


# ----------------- OTHER ROUTES -----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route("/change_password", methods=["GET"])
@login_required_page
def change_password_page():
    user = User.query.get(session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("login"))
    return render_template("change_password.html", user=user)


@csrf.exempt
@app.route("/api/change_password", methods=["POST"])
@login_required_page
@limiter.limit("5 per minute")
def api_change_password():
    data = request.get_json() or {}
    current_password = data.get("current_password", "")
    new_password     = data.get("new_password", "")
    confirm_password = data.get("confirm_password", "")

    if not all([current_password, new_password, confirm_password]):
        return jsonify({"status": "error", "message": "All fields are required."}), 400

    if len(new_password) < 5:
        return jsonify({"status": "error", "message": "New password must be at least 5 characters."}), 400

    if new_password != confirm_password:
        return jsonify({"status": "error", "message": "New passwords do not match."}), 400

    user = User.query.get(session["user_id"])
    if not user:
        session.clear()
        return jsonify({"status": "error", "message": "Session expired. Please log in again."}), 401

    if not bcrypt.check_password_hash(user.password_hash, current_password):
        return jsonify({"status": "error", "message": "Current password is incorrect."}), 400

    if bcrypt.check_password_hash(user.password_hash, new_password):
        return jsonify({"status": "error", "message": "New password must be different from the current one."}), 400

    user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    db.session.commit()

    return jsonify({"status": "success", "message": "Password updated successfully."}), 200


# ----------------- WORKSPACES API -----------------
@app.route("/api/workspaces", methods=["GET"])
@login_required_page
def list_workspaces():
    user_id = session["user_id"]
    wss = Workspace.query.filter_by(user_id=user_id).order_by(Workspace.created_at.desc()).all()
    return jsonify([{"id": ws.id, "name": ws.name} for ws in wss]), 200


@csrf.exempt
@app.route("/api/workspaces", methods=["POST"])
@login_required_page
def create_workspace():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"status": "error", "message": "Name is required."}), 400
    ws = Workspace(name=name, user_id=session["user_id"])
    db.session.add(ws)
    db.session.commit()
    return jsonify({"id": ws.id, "name": ws.name}), 201


@csrf.exempt
@app.route("/api/workspaces/<int:ws_id>", methods=["PUT"])
@login_required_page
def rename_workspace(ws_id):
    ws = Workspace.query.get_or_404(ws_id)
    if ws.user_id != session["user_id"]:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"status": "error", "message": "Name is required."}), 400
    ws.name = name
    db.session.commit()
    return jsonify({"id": ws.id, "name": ws.name}), 200


@csrf.exempt
@app.route("/api/workspaces/<int:ws_id>", methods=["DELETE"])
@login_required_page
def delete_workspace(ws_id):
    ws = Workspace.query.get_or_404(ws_id)
    if ws.user_id != session["user_id"]:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    db.session.delete(ws)
    db.session.commit()
    return jsonify({"status": "success"}), 200


# ----------------- DB INIT + TINY MIGRATION -----------------
with app.app_context():
    db.create_all()
    # best-effort add/normalize columns for SQLite if table already existed
    try:
        cols = {row[1] for row in db.session.execute(text("PRAGMA table_info(task)")).all()}
        if "status" not in cols:
            db.session.execute(text("ALTER TABLE task ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'todo'"))
            db.session.commit()
            # upgrade any completed=1 rows to status='done'
            db.session.execute(text("UPDATE task SET status='done' WHERE completed=1"))
            db.session.commit()
        else:
            # normalize any old string values to canonical
            db.session.execute(text("UPDATE task SET status='todo' WHERE status IN ('To Do','to do','to_do','')"))
            db.session.execute(text("UPDATE task SET status='in_progress' WHERE status IN ('In Progress','in progress','in_progress')"))
            db.session.execute(text("UPDATE task SET status='done' WHERE status IN ('Done','done','completed')"))
            db.session.commit()
        if "completed" not in cols:
            db.session.execute(text("ALTER TABLE task ADD COLUMN completed BOOLEAN NOT NULL DEFAULT 0"))
            db.session.commit()
    except Exception:
        pass

if __name__ == '__main__':
    app.run(debug=True)
