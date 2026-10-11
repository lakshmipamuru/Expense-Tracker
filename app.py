import os, sqlite3
from functools import wraps
from flask import Flask, request, redirect, url_for, session, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
DB = os.environ.get("DATABASE_PATH", "expenses.db")

def connect():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

with connect() as c:
    c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)")
    c.execute("""CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY, uid INTEGER, name TEXT, amount REAL,
        category TEXT, date TEXT)""")

STYLE = """
<style>
body{font-family:Arial;background:#e8f5e9;color:#1b4332;padding:15px}
.box{max-width:800px;margin:25px auto;background:white;padding:22px;border-radius:12px}
h1,h2{color:#2e7d32}
input,select{width:100%;padding:10px;margin:8px 0;box-sizing:border-box}
button{background:#2e7d32;color:white;border:0;padding:10px;cursor:pointer}
table{width:100%;border-collapse:collapse;margin-top:15px}
td,th{padding:8px;border-bottom:1px solid #c8e6c9}
th{background:#2e7d32;color:white}
footer{text-align:center;color:#2e7d32;margin-top:25px}
</style>
"""

def page(content):
    return render_template_string(
        "<html><head><meta name='viewport' content='width=device-width,initial-scale=1'>"
        + STYLE + "</head><body><div class='box'>" + content +
        "<footer>Developed by Lakshmi Pamuru</footer></div></body></html>"
    )

def required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if "uid" not in session:
            return redirect(url_for("login"))
        return fn(*a, **kw)
    return wrapper

@app.route("/")
@required
def home():
    with connect() as c:
        items = c.execute("SELECT * FROM expenses WHERE uid=? ORDER BY id DESC",
                          (session["uid"],)).fetchall()
    total = sum(x["amount"] for x in items)
    rows = "".join(
        "<tr><td>"+str(x["name"])+"</td><td>"+str(x["amount"])+"</td><td>"+
        str(x["category"])+"</td><td>"+str(x["date"])+"</td><td><form method='post' action='/delete/"+
        str(x["id"])+"'><button>Delete</button></form></td></tr>" for x in items
    )
    return page(f"""
    <h1>My Expense Tracker</h1><p>Welcome, {session['username']}</p>
    <a href="/logout">Logout</a><h2>Total: Rs. {total:.2f}</h2>
    <h2>Add Expense</h2><form method="post" action="/add">
    <input name="name" placeholder="Expense name" required>
    <input name="amount" type="number" min="0.01" step="0.01" placeholder="Amount" required>
    <select name="category"><option>Food</option><option>Travel</option>
    <option>Shopping</option><option>Bills</option><option>Other</option></select>
    <input name="date" type="date" required><button>Add Expense</button></form>
    <h2>My Expenses</h2><table><tr><th>Name</th><th>Amount</th>
    <th>Category</th><th>Date</th><th>Action</th></tr>{rows}</table>
    """)

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        u, p = request.form["username"].strip(), request.form["password"]
        if not u or len(p) < 8:
            return page("Enter username and password of at least 8 characters.")
        try:
            with connect() as c:
                c.execute("INSERT INTO users(username,password) VALUES(?,?)",
                          (u, generate_password_hash(p)))
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return page("Username already exists. <a href='/signup'>Try again</a>")
    return page("""<h1>Sign Up</h1><form method="post">
    <input name="username" placeholder="Username" required>
    <input name="password" type="password" minlength="8" placeholder="Password" required>
    <button>Create Account</button></form><a href="/login">Login</a>""")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        with connect() as c:
            u = c.execute("SELECT * FROM users WHERE username=?",
                          (request.form["username"].strip(),)).fetchone()
        if u and check_password_hash(u["password"], request.form["password"]):
            session.clear()
            session["uid"], session["username"] = u["id"], u["username"]
            return redirect(url_for("home"))
        return page("Invalid login. <a href='/login'>Try again</a>")
    return page("""<h1>Login</h1><form method="post">
    <input name="username" placeholder="Username" required>
    <input name="password" type="password" placeholder="Password" required>
    <button>Login</button></form><a href="/signup">Create Account</a>""")

@app.route("/add", methods=["POST"])
@required
def add():
    try:
        amount = float(request.form["amount"])
        name, date = request.form["name"].strip(), request.form["date"]
        category = request.form["category"]
        if not name or amount <= 0 or category not in ["Food","Travel","Shopping","Bills","Other"]:
            return redirect(url_for("home"))
        with connect() as c:
            c.execute("INSERT INTO expenses(uid,name,amount,category,date) VALUES(?,?,?,?,?)",
                      (session["uid"], name[:100], amount, category, date))
    except (ValueError, KeyError):
        pass
    return redirect(url_for("home"))

@app.route("/delete/<int:eid>", methods=["POST"])
@required
def delete(eid):
    with connect() as c:
        c.execute("DELETE FROM expenses WHERE id=? AND uid=?", (eid, session["uid"]))
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))