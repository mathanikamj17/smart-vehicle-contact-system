
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "move_my_vehicle_secret"

DATABASE = os.path.join(os.path.dirname(__file__), "vehicles.db")


# Database connection
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# Create database table
def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_number TEXT NOT NULL,
            owner_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            vehicle_type TEXT,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# Home page
@app.route("/")
def home():
    return render_template("index.html")


# Vehicle registration
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        vehicle_number = request.form.get("vehicle_number", "").strip()
        owner_name = request.form.get("owner_name", "").strip()
        phone = request.form.get("phone", "").strip()
        vehicle_type = request.form.get("vehicle_type", "").strip()
        address = request.form.get("address", "").strip()

        if not vehicle_number or not owner_name or not phone:
            flash("Please fill all required fields.")
            return redirect(url_for("register"))

        conn = get_db()

        conn.execute("""
            INSERT INTO vehicles
            (vehicle_number, owner_name, phone, vehicle_type, address)
            VALUES (?, ?, ?, ?, ?)
        """, (
            vehicle_number,
            owner_name,
            phone,
            vehicle_type,
            address
        ))

        conn.commit()
        conn.close()

        flash("Vehicle registered successfully!")
        return redirect(url_for("home"))

    return render_template("register.html")


# Owner search
@app.route("/owner", methods=["GET", "POST"])
def owner():

    vehicle = None

    if request.method == "POST":

        vehicle_number = request.form.get("vehicle_number", "").strip()

        conn = get_db()

        vehicle = conn.execute("""
            SELECT * FROM vehicles
            WHERE vehicle_number = ?
        """, (vehicle_number,)).fetchone()

        conn.close()

        if vehicle is None:
            flash("Vehicle details not found.")

    return render_template("owner.html", vehicle=vehicle)


# Admin dashboard
@app.route("/admin")
def admin():

    conn = get_db()

    vehicles = conn.execute("""
        SELECT * FROM vehicles
        ORDER BY id DESC
    """).fetchall()

    total = len(vehicles)

    conn.close()

    return render_template(
        "admin.html",
        vehicles=vehicles,
        total=total
    )


# Report page
@app.route("/report")
def report():

    conn = get_db()

    vehicles = conn.execute("""
        SELECT * FROM vehicles
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "report.html",
        vehicles=vehicles
    )


# Initialize database
init_db()


# Run application
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

