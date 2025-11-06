from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter  # <-- Import Limiter
from flask_limiter.util import get_remote_address # <-- Import get_remote_address
import os

app = Flask(__name__)

limiter = Limiter(
    get_remote_address, # Use the visitor's IP address to track requests
    app=app,
    default_limits=["200 per day", "50 per hour"], # Default limits for all routes
    storage_uri="memory://",  # Store rate limit data in memory (for simplicity)
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

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

@app.route('/')
def home():
    return render_template("register.html")
    
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
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'status': 'error', 'message': 'Email and password are required.'}), 400

    user = User.query.filter_by(email=email).first()

    if user and bcrypt.check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        print(f"User '{user.username}' logged in successfully.")
        return jsonify({'status': 'success', 'message': 'Login successful!'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Invalid email or password.'}), 401 #failed login still counts twoards rL



with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)