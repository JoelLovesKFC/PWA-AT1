from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from datetime import datetime
from functools import wraps
from uuid import uuid4
from datetime import datetime, timedelta


app = Flask(__name__)

limiter = Limiter(
    get_remote_address, # Use the visitor's IP address to track requests
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

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(60), nullable=False)
        # This relationship creates the 'user.notes' property
    notes = db.relationship('Note', backref='author', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"
    

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) #foreign key links this to the id of the user

    def to_dict(self):
        """A helper method to easily convert a Note object to a dictionary."""
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

# Add relationship on User (below 'notes' line)
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



def login_required_page(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template("home.html")



@app.route('/register', methods=['GET'])
def register_page():
    return render_template("register.html")

    
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

# API: actually perform the password change
# If you're calling this via fetch/JSON and using CSRFProtect globally,
# you can exempt this endpoint OR include a CSRF token in the request.
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

    # Verify old password
    if not bcrypt.check_password_hash(user.password_hash, current_password):
        return jsonify({"status": "error", "message": "Current password is incorrect."}), 400

    # Prevent reusing the exact same password
    if bcrypt.check_password_hash(user.password_hash, new_password):
        return jsonify({"status": "error", "message": "New password must be different from the current one."}), 400

    # Hash and replace the stored password (old hash is effectively discarded)
    user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    db.session.commit()

    return jsonify({"status": "success", "message": "Password updated successfully."}), 200



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



with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)