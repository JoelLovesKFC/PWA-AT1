from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
users = {}

@app.route("/")
def home():
    return 'Welcome! <a href="/login">Login</a> or <a href="/register">Register</a>'

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html") 

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in users:
            return render_template("register.html", error="Username already exists.")
        if username.isdigit():
            return render_template("register.html", error="Username cannot be only numbers.")

        users[username] = password
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in users and users[username] == password:
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid username or password.")
    return render_template("login.html")

if __name__ == "__main__":
    app.run(debug=True)
