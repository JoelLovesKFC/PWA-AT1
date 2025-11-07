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


def login_required_page(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Instead of returning JSON, we redirect to the 'login' route's URL.
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template("register.html")

# # READ all notes for the logged-in user
# @app.route("/api/notes", methods=['GET'])
# @login_required
# def get_notes():
#     user_id = session['user_id']
#     notes = Note.query.filter_by(user_id=user_id).order_by(Note.date_created.desc()).all()
#     return jsonify([note.to_dict() for note in notes]), 200


# @app.route("/api/notes", methods=['POST'])
# @login_required
# def create_note():
#     data = request.get_json()
#     title = data.get('title')
#     content = data.get('content')

#     if not title or not content:
#         return jsonify({'status': 'error', 'message': 'Title and content are required.'}), 400

#     new_note = Note(title=title, content=content, user_id=session['user_id'])
#     db.session.add(new_note)
#     db.session.commit()

#     return jsonify(new_note.to_dict()), 201


# @app.route("/api/notes/<int:note_id>", methods=['PUT'])
# @login_required
# def update_note(note_id):
#     note = Note.query.get(note_id)
#     if not note:
#         return jsonify({'status': 'error', 'message': 'Note not found.'}), 404
    
#     # CRITICAL SECURITY CHECK: Ensure the note belongs to the logged-in user.
#     if note.user_id != session['user_id']:
#         return jsonify({'status': 'error', 'message': 'Unauthorized to edit this note.'}), 403

#     data = request.get_json()
#     note.title = data.get('title', note.title)
#     note.content = data.get('content', note.content)
#     db.session.commit()

#     return jsonify(note.to_dict()), 2003
    
# @app.route("/api/notes/<int:note_id>", methods=['DELETE'])
# @login_required
# def delete_note(note_id):
#     note = Note.query.get(note_id)
#     if not note:
#         return jsonify({'status': 'error', 'message': 'Note not found.'}), 404
        
#     if note.user_id != session['user_id']:
#         return jsonify({'status': 'error', 'message': 'Unauthorized to delete this note.'}), 403

#     db.session.delete(note)
#     db.session.commit()

#     return jsonify({'status': 'success', 'message': 'Note deleted.'}), 200


    
@app.route('/register', methods=['POST'])
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
@login_required_page  # <-- Apply the new decorator here
def dashboard():
    user = User.query.get(session['user_id'])
    return render_template("dashboard.html", user=user)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route("/change_password")
def change_password(): 
    pass

@app.route("/forgot_password")
def forgot_password():
    pass


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)