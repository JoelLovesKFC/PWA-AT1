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
        return { 
            'id': self.id, 
            'title': self.title, 
            'content': self.content, 
            'is_trashed': self.is_trashed, 
            'date_created': self.date_created.isoformat(), 
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Workspace(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    position = db.Column(db.Integer, default=0)
    is_trashed = db.Column(db.Boolean, default=False, nullable=False)
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
    position = db.Column(db.Integer, default=0)
    # UPDATED: Added is_trashed for soft delete
    is_trashed = db.Column(db.Boolean, default=False, nullable=False)
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
@app.route("/tasks")
@login_required_page
def tasks_page():
    user = User.query.get(session['user_id'])
    return render_template("task.html", user=user)

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

@app.route("/change_password", methods=["GET"])
@login_required_page
def change_password_page():
    user = User.query.get(session["user_id"])
    return render_template("change_password.html", user=user)

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

    user = User.query.filter(or_(User.username == login_identifier, User.email == login_identifier)).first()

    if user and bcrypt.check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        return jsonify({'status': 'success', 'message': 'Login successful!'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Invalid credentials.'}), 401

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

    if not all([name, username, email, password, confirm_password]):
        return jsonify({'status': 'error', 'message': 'All fields are required.'}), 400
    if len(password) < 5:
        return jsonify({'status': 'error', 'errors': {'password': 'Password must be at least 5 characters.'}}), 400
    if password != confirm_password:
        return jsonify({'status': 'error', 'message': 'Passwords do not match.'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'status': 'error', 'message': 'Username already exists.'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'status': 'error', 'message': 'Email already registered.'}), 400

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
    
    # UPDATED: Filter by is_trashed=False
    q = Task.query.filter_by(user_id=user_id, is_trashed=False)
    
    if st in STATUS_CHOICES:
        q = q.filter(Task.status == st)
        
    tasks = q.order_by(Task.position.asc(), Task.created_at.desc()).all()

    def to_dict(t):
        return {
            "id": t.id, "title": t.title, "description": t.description or "",
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "status": t.status, "completed": bool(t.completed),
            "created_at": t.created_at.isoformat(),
            "position": t.position
        }
    return jsonify([to_dict(t) for t in tasks]), 200

@csrf.exempt
@app.route("/api/tasks", methods=["POST"])
@login_required_page
def create_task():
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    status = canonical_status(data.get("status")) or "todo"

    if not title:
        return jsonify({"status": "error", "message": "Title is required."}), 400

    dd = (data.get("due_date") or "").strip()
    due_date = None
    if dd:
        try: due_date = datetime.strptime(dd, "%Y-%m-%d").date()
        except ValueError: return jsonify({"status": "error", "message": "Invalid date format."}), 400
    
    description_val = (data.get("description") or "").strip()

    task = Task(
        title=title, 
        description=description_val, 
        due_date=due_date, 
        status=status, 
        completed=(status == "done"), 
        user_id=session["user_id"]
    )
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
    
    # UPDATED: Soft delete
    task.is_trashed = True
    db.session.commit()
    return jsonify({"status": "success"}), 200

@csrf.exempt
@app.route("/api/tasks/bulk_delete", methods=["POST"])
@login_required_page
def bulk_delete_tasks():
    data = request.get_json() or {}
    ids = data.get("ids") or []
    if not ids: return jsonify({"status": "error", "message": "No ids provided."}), 400
    
    # UPDATED: Bulk soft delete
    Task.query.filter(Task.user_id == session["user_id"], Task.id.in_(ids)).update({Task.is_trashed: True}, synchronize_session=False)
    db.session.commit()
    return jsonify({"status": "success"}), 200

@csrf.exempt
@app.route("/api/tasks/reorder", methods=["POST"])
@login_required_page
def reorder_tasks():
    data = request.get_json() or {}
    ordered_ids = data.get("ids") or []
    if not ordered_ids: return jsonify({"status": "success"}), 200
    tasks = Task.query.filter(Task.user_id == session["user_id"], Task.id.in_(ordered_ids)).all()
    task_map = {t.id: t for t in tasks}
    for index, t_id in enumerate(ordered_ids):
        try: t_id = int(t_id)
        except: continue
        if t_id in task_map: task_map[t_id].position = index
    db.session.commit()
    return jsonify({"status": "success"}), 200


# ----------------- NOTES API (Standalone) -----------------

@csrf.exempt
@app.route("/api/standalone_notes", methods=["GET"])
@login_required_page
def list_standalone_notes():
    sort_by = request.args.get("sort", "newest")
    
    q = Note.query.filter_by(user_id=session["user_id"], is_trashed=False)
    
    if sort_by == "oldest":
        q = q.order_by(Note.updated_at.asc())
    elif sort_by == "alpha":
        q = q.order_by(Note.title.asc())
    else:
        q = q.order_by(Note.updated_at.desc())
        
    notes = q.all()
    return jsonify([n.to_dict() for n in notes]), 200

@csrf.exempt
@app.route("/api/standalone_notes", methods=["POST"])
@login_required_page
def create_standalone_note():
    data = request.get_json() or {}
    title = (data.get("title") or "Untitled").strip()
    content = data.get("content") or ""
    
    note = Note(title=title, content=content, user_id=session["user_id"])
    db.session.add(note)
    db.session.commit()
    return jsonify(note.to_dict()), 201

@csrf.exempt
@app.route("/api/standalone_notes/<int:note_id>", methods=["PUT"])
@login_required_page
def update_standalone_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id != session["user_id"]: 
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    
    data = request.get_json() or {}
    if "title" in data:
        note.title = (data.get("title") or "Untitled").strip()
    if "content" in data:
        note.content = data.get("content")
    
    db.session.commit()
    return jsonify(note.to_dict()), 200

@csrf.exempt
@app.route("/api/standalone_notes/<int:note_id>", methods=["DELETE"])
@login_required_page
def delete_standalone_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id != session["user_id"]: 
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    
    # Soft delete
    note.is_trashed = True
    db.session.commit()
    return jsonify({"status": "success"}), 200


# ----------------- GLOBAL TRASH API -----------------

@app.route("/api/trash", methods=["GET"])
@login_required_page
def get_trash_items():
    user_id = session["user_id"]
    
    # Get trashed Tasks
    tasks = Task.query.filter_by(user_id=user_id, is_trashed=True).order_by(Task.created_at.desc()).all()
    # Get trashed Notes
    notes = Note.query.filter_by(user_id=user_id, is_trashed=True).order_by(Note.updated_at.desc()).all()
    
    trash_items = []
    
    for t in tasks:
        trash_items.append({
            "id": t.id,
            "type": "task",
            "title": t.title,
            "date": t.created_at.isoformat()
        })
        
    for n in notes:
        trash_items.append({
            "id": n.id,
            "type": "note",
            "title": n.title,
            "date": n.updated_at.isoformat() if n.updated_at else n.date_created.isoformat()
        })
        
    # Sort combined list by date descending
    trash_items.sort(key=lambda x: x['date'], reverse=True)
    
    return jsonify(trash_items), 200

@csrf.exempt
@app.route("/api/trash/restore", methods=["POST"])
@login_required_page
def restore_item():
    data = request.get_json() or {}
    item_id = data.get("id")
    item_type = data.get("type")
    
    if not item_id or not item_type:
        return jsonify({"status": "error"}), 400
        
    if item_type == "task":
        item = Task.query.get(item_id)
        if item and item.user_id == session["user_id"]:
            item.is_trashed = False
            db.session.commit()
            return jsonify({"status": "success"}), 200
            
    elif item_type == "note":
        item = Note.query.get(item_id)
        if item and item.user_id == session["user_id"]:
            item.is_trashed = False
            db.session.commit()
            return jsonify({"status": "success"}), 200
            
    return jsonify({"status": "error", "message": "Item not found"}), 404

@csrf.exempt
@app.route("/api/trash/permanent", methods=["DELETE"])
@login_required_page
def permanent_delete_item():
    data = request.get_json() or {}
    item_id = data.get("id")
    item_type = data.get("type")
    
    if not item_id or not item_type:
        return jsonify({"status": "error"}), 400
        
    if item_type == "task":
        item = Task.query.get(item_id)
        if item and item.user_id == session["user_id"]:
            db.session.delete(item)
            db.session.commit()
            return jsonify({"status": "success"}), 200
            
    elif item_type == "note":
        item = Note.query.get(item_id)
        if item and item.user_id == session["user_id"]:
            db.session.delete(item)
            db.session.commit()
            return jsonify({"status": "success"}), 200
            
    return jsonify({"status": "error", "message": "Item not found"}), 404


# --- Profile & Password ---
@csrf.exempt
@app.route("/api/profile/basic", methods=["POST"])
@login_required_page
def api_update_profile_basic():
    data = request.get_json() or {}
    user = User.query.get(session["user_id"])
    if User.query.filter(User.username == data.get("username"), User.id != user.id).first():
        return jsonify({"status": "error", "field": "username", "message": "Username taken"}), 400
    user.name = data.get("name")
    user.username = data.get("username")
    user.email = data.get("email")
    db.session.commit()
    return jsonify({"status": "success"}), 200

@csrf.exempt
@app.route("/api/change_password", methods=["POST"])
@login_required_page
def api_change_password():
    data = request.get_json()
    user = User.query.get(session["user_id"])
    if not bcrypt.check_password_hash(user.password_hash, data.get("current_password")):
        return jsonify({"status": "error", "message": "Incorrect password"}), 400
    user.password_hash = bcrypt.generate_password_hash(data.get("new_password")).decode("utf-8")
    db.session.commit()
    return jsonify({"status": "success"}), 200

# --- DB MIGRATION CHECK ---
with app.app_context():
    db.create_all()
    try:
        with db.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(note)"))
            cols_note = [row[1] for row in result.fetchall()]
            if "is_trashed" not in cols_note:
                conn.execute(text("ALTER TABLE note ADD COLUMN is_trashed BOOLEAN DEFAULT 0 NOT NULL"))
            
            result = conn.execute(text("PRAGMA table_info(task)"))
            cols_task = [row[1] for row in result.fetchall()]
            if "position" not in cols_task:
                conn.execute(text("ALTER TABLE task ADD COLUMN position INTEGER DEFAULT 0"))
            # UPDATED: Check for is_trashed in Task
            if "is_trashed" not in cols_task:
                print("Migrating DB: Adding is_trashed column to Task table...")
                conn.execute(text("ALTER TABLE task ADD COLUMN is_trashed BOOLEAN DEFAULT 0 NOT NULL"))

            result = conn.execute(text("PRAGMA table_info(workspace)"))
            cols_ws = [row[1] for row in result.fetchall()]
            if "position" not in cols_ws:
                conn.execute(text("ALTER TABLE workspace ADD COLUMN position INTEGER DEFAULT 0"))
            
            if "is_trashed" not in cols_ws:
                conn.execute(text("ALTER TABLE workspace ADD COLUMN is_trashed BOOLEAN DEFAULT 0 NOT NULL"))
            
            conn.commit()
    except Exception as e:
        print(f"Migration check failed (ignored): {e}")

if __name__ == '__main__':
    app.run(debug=True)