import re, sqlite3, os
from flask import Flask, render_template, request, redirect, url_for, session, flash, g

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")  # change before demo
DB = "vehicles.db"
PLATE = re.compile(r"^[A-Z]{2}\d{1,2}[A-Z]{0,3}\d{4}$")  # e.g. TN38AB1234
PHONE = re.compile(r"^[6-9]\d{9}$")

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close(_):
    d = g.pop("db", None)
    if d: d.close()

def init():
    with sqlite3.connect(DB) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS owners(
            id INTEGER PRIMARY KEY, name TEXT, vehicle TEXT UNIQUE,
            phone TEXT, consent INTEGER, created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS reports(
            id INTEGER PRIMARY KEY, owner_id INTEGER, vehicle TEXT, location TEXT,
            problem TEXT, status TEXT DEFAULT 'Pending', response TEXT,
            created TEXT DEFAULT CURRENT_TIMESTAMP);""")

def clean(plate):
    return re.sub(r"[\s-]", "", plate or "").upper()

def notify(owner, report_id):
    # Demo stub: replace with SMS/WhatsApp API (e.g. Twilio) later.
    print(f"[ALERT] To {owner['phone']}: your vehicle {owner['vehicle']} is blocking a road. Report #{report_id}")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        plate, phone = clean(request.form["vehicle"]), request.form["phone"].strip()
        if not name or not PLATE.match(plate):
            flash("Enter your name and a valid vehicle number, like TN38AB1234.", "err")
        elif not PHONE.match(phone):
            flash("Enter a valid 10-digit mobile number.", "err")
        elif not request.form.get("consent"):
            flash("Please tick the consent box to register.", "err")
        else:
            try:
                db().execute("INSERT INTO owners(name,vehicle,phone,consent) VALUES(?,?,?,1)", (name, plate, phone))
                db().commit()
                flash(f"{plate} is registered. You will be alerted if it blocks someone.", "ok")
                return redirect(url_for("register"))
            except sqlite3.IntegrityError:
                flash("This vehicle number is already registered.", "err")
    return render_template("register.html")

@app.route("/report", methods=["GET", "POST"])
def report():
    result = None
    if request.method == "POST":
        plate = clean(request.form["vehicle"])
        loc, prob = request.form["location"].strip(), request.form["problem"].strip()
        if not PLATE.match(plate) or not loc or not prob:
            flash("Fill in a valid vehicle number, the location and the problem.", "err")
        else:
            owner = db().execute("SELECT * FROM owners WHERE vehicle=? AND consent=1", (plate,)).fetchone()
            cur = db().execute("INSERT INTO reports(owner_id,vehicle,location,problem) VALUES(?,?,?,?)",
                               (owner["id"] if owner else None, plate, loc, prob))
            db().commit()
            if owner:
                notify(owner, cur.lastrowid)
            result = {"found": bool(owner), "id": cur.lastrowid, "plate": plate}
    return render_template("report.html", result=result)

@app.route("/owner", methods=["GET", "POST"])
def owner():
    rows = None
    if request.method == "POST":
        plate, phone = clean(request.form["vehicle"]), request.form["phone"].strip()
        o = db().execute("SELECT * FROM owners WHERE vehicle=? AND phone=?", (plate, phone)).fetchone()
        if not o:
            flash("No match. Check your vehicle number and mobile number.", "err")
        else:
            rows = db().execute("SELECT * FROM reports WHERE owner_id=? ORDER BY id DESC", (o["id"],)).fetchall()
    return render_template("owner.html", rows=rows)

@app.route("/owner/respond/<int:rid>", methods=["POST"])
def respond(rid):
    db().execute("UPDATE reports SET response=? WHERE id=?", (request.form["response"], rid))
    db().commit()
    flash("Response sent.", "ok")
    return redirect(url_for("owner"))

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST" and "password" in request.form:
        if request.form["password"] == ADMIN_PASSWORD:
            session["admin"] = True
        else:
            flash("Wrong password.", "err")
    if not session.get("admin"):
        return render_template("admin.html", rows=None)
    rows = db().execute("SELECT * FROM reports ORDER BY id DESC").fetchall()
    return render_template("admin.html", rows=rows)

@app.route("/admin/resolve/<int:rid>", methods=["POST"])
def resolve(rid):
    if session.get("admin"):
        db().execute("UPDATE reports SET status='Resolved' WHERE id=?", (rid,))
        db().commit()
    return redirect(url_for("admin"))

if __name__ == "__main__":
    init()
    app.run(debug=True)
