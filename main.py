from flask import Flask, render_template
import sqlite3

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("login.html")


app.route("/login", methods = ["GET", "POST"])
def login(): 
    if request.method == "POST": 
        username = request.form["username"]
        password = request.form["password"]
    
    return render_template("login.html")



if __name__ == '__main__':
    app.run(debug=True)