from flask import Flask, render_template, flash, request
import sqlite3

app = Flask(__name__)


@app.route("/")
def home(): 
    return render_template()

@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    return render_template("register.html")



@app.route("/dashboard")
def dashboard():
    pass






if __name__ == '__main__':
    app.run(debug=True)