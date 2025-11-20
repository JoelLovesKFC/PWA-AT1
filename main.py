from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, text
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import json
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

# ---------------- MODELS ----------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(60), nullable=False)
    notes = db.relationship('Note', backref='author', lazy=True, cascade="all, delete-orphan")
    def __repr__(self): return f"User('{self.username}', '{self.email}')"

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False, default="Untitled")
    content = db.Column(db.Text, nullable=True)
    is_trashed = db.Column(db.Boolean, default=False, nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=True)
    def to_dict(self):
        return { 'id': self.id, 'title': self.title, 'content': self.content, 'is_trashed': self.is_trashed, 'date_created': self.date_created.isoformat(), 'updated_at': self.updated_at.isoformat() if self.updated_at else None, 'workspace_id': self.workspace_id }

class Workspace(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

User.workspaces = db.relationship('Workspace', backref='owner', lazy=True, cascade="all, delete-orphan")
Workspace.notes = db.relationship('Note', backref='workspace', lazy=True, cascade="all, delete-orphan")

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True) 
    due_date = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False, default="todo")
    completed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# ---- Helpers ----
STATUS_CHOICES = {"todo", "in_progress", "done"}

def canonical_status(value: str | None) -> str | None:
    s = (value or "").strip().lower()
    if s in ("todo", "to do", "to_do"): return "todo"
    if s in ("in progress", "in_progress", "inprogress"): return "in_progress"
    if s in ("done", "complete", "completed"): return "done"
    return None

def login_required_page(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ----------------- PAGES -----------------

# HOME PAGE (Redirects to Tasks if already logged in)
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('tasks_page'))
    return render_template("home.html")

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'GET':
        if 'user_id' in session: return redirect(url_for('tasks_page'))
        return render_template("login.html")

    data = request.get_json()
    login_identifier = data.get('login_identifier')
    password = data.get('password')
    if not login_identifier or not password:
        return jsonify({'status': 'error', 'message': 'Username/Email and password are required.'}), 400
    user = User.query.filter(or_(User.username == login_identifier, User.email == login_identifier)).first()
    if user and bcrypt.check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        return jsonify({'status': 'success', 'message': 'Login successful!'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Invalid credentials.'}), 401

# TASKS PAGE (Main App Page)
@app.route("/tasks")
@login_required_page
def tasks_page():
    user = User.query.get(session['user_id'])
    return render_template("task.html", user=user)

@app.route("/task")
@login_required_page
def task_page_alias():
    return redirect(url_for("tasks_page"))

@app.route('/register', methods=['GET'])
def register_page():
    return render_template("register.html")

@app.route("/workspaces/<int:ws_id>")
@login_required_page
def workspace_detail(ws_id):
    ws = Workspace.query.get_or_404(ws_id)
    if ws.user_id != session["user_id"]: return "Forbidden", 403
    return render_template("workspace.html", ws=ws)

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

@app.route("/change_password", methods=["GET"])
@login_required_page
def change_password_page():
    user = User.query.get(session["user_id"])
    return render_template("change_password.html", user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ----------------- AUTH API -----------------
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    if not all([name, username, email, password, confirm_password]): return jsonify({'status': 'error', 'message': 'All fields are required.'}), 400
    if len(password) < 5: return jsonify({'status': 'error', 'errors': {'password': 'Password must be at least 5 characters.'}}), 400
    if password != confirm_password: return jsonify({'status': 'error', 'message': 'Passwords do not match.'}), 400
    if User.query.filter_by(username=username).first(): return jsonify({'status': 'error', 'message': 'Username already exists.'}), 400
    if User.query.filter_by(email=email).first(): return jsonify({'status': 'error', 'message': 'Email already registered.'}), 400
    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(name=name, username=username, email=email, password_hash=hashed)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Registration successful!'}), 201

# ----------------- TASK API -----------------
@csrf.exempt
@app.route("/api/tasks", methods=["GET"])
@login_required_page
def list_tasks():
    user_id = session["user_id"]
    st = canonical_status(request.args.get("status"))
    q = Task.query.filter_by(user_id=user_id)
    if st in STATUS_CHOICES: q = q.filter(Task.status == st)
    tasks = q.order_by(Task.created_at.desc()).all()
    def to_dict(t):
        return { "id": t.id, "title": t.title, "description": t.description or "", "due_date": t.due_date.isoformat() if t.due_date else None, "status": t.status, "completed": bool(t.completed), "created_at": t.created_at.isoformat() }
    return jsonify([to_dict(t) for t in tasks]), 200

@csrf.exempt
@app.route("/api/tasks", methods=["POST"])
@login_required_page
def create_task():
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    status = canonical_status(data.get("status")) or "todo"
    if not title: return jsonify({"status": "error", "message": "Title is required."}), 400
    dd = (data.get("due_date") or "").strip()
    due_date = None
    if dd:
        try: due_date = datetime.strptime(dd, "%Y-%m-%d").date()
        except ValueError: return jsonify({"status": "error", "message": "Invalid date format."}), 400
    task = Task(title=title, description=(data.get("description") or "").strip(), due_date=due_date, status=status, completed=(status == "done"), user_id=session["user_id"])
    db.session.add(task)
    db.session.commit()
    return jsonify({"id": task.id}), 201

@csrf.exempt
@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
@login_required_page
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != session["user_id"]: return jsonify({"status": "error"}), 403
    data = request.get_json() or {}
    if "title" in data: task.title = (data.get("title") or "").strip()
    if "description" in data: task.description = (data.get("description") or "").strip()
    if "due_date" in data:
        dd = (data.get("due_date") or "").strip()
        if dd:
            try: task.due_date = datetime.strptime(dd, "%Y-%m-%d").date()
            except ValueError: return jsonify({"status": "error", "message": "Invalid date"}), 400
        else: task.due_date = None
    if "status" in data:
        st = canonical_status(data.get("status"))
        if st: task.status = st; task.completed = (st == "done")
    db.session.commit()
    return jsonify({"status": "success"}), 200

@csrf.exempt
@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
@login_required_page
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != session["user_id"]: return jsonify({"status": "error"}), 403
    db.session.delete(task)
    db.session.commit()
    return jsonify({"status": "success"}), 200

@csrf.exempt
@app.route("/api/tasks/bulk_delete", methods=["POST"])
@login_required_page
def bulk_delete_tasks():
    data = request.get_json() or {}
    ids = data.get("ids") or []
    if not ids: return jsonify({"status": "error", "message": "No ids provided."}), 400
    q = Task.query.filter(Task.user_id == session["user_id"], Task.id.in_(ids))
    q.delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"status": "success"}), 200

# --- Profile & Password ---
@csrf.exempt
@app.route("/api/profile/basic", methods=["POST"])
@login_required_page
def api_update_profile_basic():
    data = request.get_json() or {}
    user = User.query.get(session["user_id"])
    if User.query.filter(User.username == data.get("username"), User.id != user.id).first(): return jsonify({"status": "error", "field": "username", "message": "Username taken"}), 400
    user.name = data.get("name"); user.username = data.get("username"); user.email = data.get("email")
    db.session.commit()
    return jsonify({"status": "success"}), 200

@csrf.exempt
@app.route("/api/change_password", methods=["POST"])
@login_required_page
def api_change_password():
    data = request.get_json()
    user = User.query.get(session["user_id"])
    if not bcrypt.check_password_hash(user.password_hash, data.get("current_password")): return jsonify({"status": "error", "message": "Incorrect password"}), 400
    user.password_hash = bcrypt.generate_password_hash(data.get("new_password")).decode("utf-8")
    db.session.commit()
    return jsonify({"status": "success"}), 200

@app.route("/api/workspaces", methods=["GET"])
@login_required_page
def list_workspaces():
    wss = Workspace.query.filter_by(user_id=session["user_id"]).order_by(Workspace.created_at.desc()).all()
    return jsonify([{"id": w.id, "name": w.name} for w in wss]), 200

@csrf.exempt
@app.route("/api/workspaces", methods=["POST"])
@login_required_page
def create_workspace():
    data = request.get_json()
    ws = Workspace(name=data.get("name"), user_id=session["user_id"])
    db.session.add(ws)
    db.session.commit()
    return jsonify({"id": ws.id, "name": ws.name}), 201

@csrf.exempt
@app.route("/api/workspaces/<int:ws_id>", methods=["PUT", "DELETE"])
@login_required_page
def workspace_ops(ws_id):
    ws = Workspace.query.get_or_404(ws_id)
    if ws.user_id != session["user_id"]: return jsonify({"status": "error"}), 403
    if request.method == 'DELETE': db.session.delete(ws)
    else: ws.name = request.get_json().get("name")
    db.session.commit()
    return jsonify({"status": "success"}), 200

@csrf.exempt
@app.route("/api/workspaces/<int:ws_id>/notes", methods=["GET", "POST"])
@login_required_page
def ws_notes(ws_id):
    if not Workspace.query.filter_by(id=ws_id, user_id=session["user_id"]).first(): return jsonify({"status": "error", "message": "Forbidden"}), 403
    if request.method == 'POST':
        empty_block_json = '{"time":1700000000,"blocks":[{"id":"a1","type":"paragraph","data":{"text":""}}],"version":"2.28.0"}'
        n = Note(title="Untitled", content=empty_block_json, user_id=session["user_id"], workspace_id=ws_id)
        db.session.add(n); db.session.commit()
        return jsonify(n.to_dict()), 201
    notes = Note.query.filter_by(user_id=session["user_id"], workspace_id=ws_id, is_trashed=False).order_by(Note.updated_at.desc()).all()
    return jsonify([n.to_dict() for n in notes]), 200

@app.route("/api/notes/<int:note_id>", methods=["GET"])
@login_required_page
def get_single_note(note_id):
    n = Note.query.get_or_404(note_id)
    if n.user_id != session["user_id"]: return jsonify({"status": "error", "message": "Forbidden"}), 403
    return jsonify(n.to_dict()), 200

@csrf.exempt
@app.route("/api/notes/<int:note_id>", methods=["PUT", "DELETE"])
@login_required_page
def note_ops(note_id):
    n = Note.query.get_or_404(note_id)
    if n.user_id != session["user_id"]: return jsonify({"status": "error", "message": "Forbidden"}), 403
    if request.method == 'DELETE':
        n.is_trashed = True; db.session.commit()
        return jsonify({"status": "success"}), 200
    data = request.get_json() or {}
    if "title" in data: n.title = data["title"]
    if "content" in data:
        content_val = data["content"]
        n.content = json.dumps(content_val) if isinstance(content_val, (dict, list)) else content_val
    db.session.commit()
    return jsonify({"status": "success"}), 200

@app.route("/api/workspaces/<int:ws_id>/trash", methods=["GET"])
@login_required_page
def get_trash(ws_id):
    notes = Note.query.filter_by(user_id=session["user_id"], workspace_id=ws_id, is_trashed=True).order_by(Note.updated_at.desc()).all()
    return jsonify([n.to_dict() for n in notes]), 200

@csrf.exempt
@app.route("/api/notes/<int:note_id>/restore", methods=["POST"])
@login_required_page
def restore_note(note_id):
    n = Note.query.get_or_404(note_id)
    if n.user_id != session["user_id"]: return jsonify({"status": "error"}), 403
    n.is_trashed = False; db.session.commit()
    return jsonify({"status": "success"}), 200

@csrf.exempt
@app.route("/api/notes/<int:note_id>/permanent", methods=["DELETE"])
@login_required_page
def hard_delete_note(note_id):
    n = Note.query.get_or_404(note_id)
    if n.user_id != session["user_id"]: return jsonify({"status": "error"}), 403
    db.session.delete(n); db.session.commit()
    return jsonify({"status": "success"}), 200

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)