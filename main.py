from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template("register.html")

@app.route('/login')
def login():
    return render_template("login.html")

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')

    # For now, just print or store in memory
    print(f"User Registered: {username}, {email}, {name}")
    # Later: save to database here

    return jsonify({'status': 'success'}), 200

@app.route("/dashboard")
def dashboard():
    render_template("dashboard.html")

if __name__ == '__main__':
    app.run(debug=True)
