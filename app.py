from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# Database location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "requests.db")


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_database():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trip_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            travel_date TEXT NOT NULL,
            people INTEGER NOT NULL,
            services TEXT,
            preferred_time TEXT,
            message TEXT,
            status TEXT DEFAULT 'New',
            quote_amount REAL DEFAULT 0,
            payment_status TEXT DEFAULT 'Pending'
        )
    """)

    conn.commit()

    # Add missing columns if an older database exists
    cursor.execute("PRAGMA table_info(trip_requests)")
    columns = [row[1] for row in cursor.fetchall()]

    if "status" not in columns:
        cursor.execute(
            "ALTER TABLE trip_requests ADD COLUMN status TEXT DEFAULT 'New'"
        )

    if "quote_amount" not in columns:
        cursor.execute(
            "ALTER TABLE trip_requests ADD COLUMN quote_amount REAL DEFAULT 0"
        )

    if "payment_status" not in columns:
        cursor.execute(
            "ALTER TABLE trip_requests ADD COLUMN payment_status TEXT DEFAULT 'Pending'"
        )

    conn.commit()
    conn.close()


# IMPORTANT:
# This runs when Gunicorn/Render starts the application.
create_database()


# ---------------- HOME ----------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- CUSTOMER PLAN ----------------

@app.route("/plan", methods=["GET", "POST"])
def plan():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        travel_date = request.form.get("travel_date", "").strip()
        people = request.form.get("people", "1").strip()

        services_list = request.form.getlist("services")
        services = ", ".join(services_list)

        preferred_time = request.form.get("preferred_time", "").strip()
        message = request.form.get("message", "").strip()

        # Basic validation
        if not name or not phone or not travel_date:
            return "Please fill all required fields.", 400

        try:
            people = int(people)
        except ValueError:
            people = 1

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO trip_requests
            (
                name,
                phone,
                travel_date,
                people,
                services,
                preferred_time,
                message,
                status,
                quote_amount,
                payment_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            phone,
            travel_date,
            people,
            services,
            preferred_time,
            message,
            "New",
            0,
            "Pending"
        ))

        conn.commit()

        request_id = cursor.lastrowid

        conn.close()

        return redirect(url_for("quote", request_id=request_id))

    return render_template("plan.html")


# ---------------- ADMIN ----------------

@app.route("/admin")
def admin():

    conn = get_db()

    requests_data = conn.execute("""
        SELECT *
        FROM trip_requests
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        requests=requests_data
    )


# ---------------- UPDATE QUOTE / STATUS ----------------

@app.route("/admin/update/<int:request_id>", methods=["POST"])
def update_request(request_id):

    quote_amount = request.form.get("quote_amount", "0").strip()
    status = request.form.get("status", "New").strip()

    try:
        quote_amount = float(quote_amount)
    except ValueError:
        quote_amount = 0

    conn = get_db()

    conn.execute("""
        UPDATE trip_requests
        SET
            quote_amount = ?,
            status = ?
        WHERE id = ?
    """, (
        quote_amount,
        status,
        request_id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


# ---------------- QUOTE PAGE ----------------

@app.route("/quote/<int:request_id>")
def quote(request_id):

    conn = get_db()

    trip = conn.execute("""
        SELECT *
        FROM trip_requests
        WHERE id = ?
    """, (request_id,)).fetchone()

    conn.close()

    if trip is None:
        return "Booking request not found.", 404

    return render_template(
        "quote.html",
        trip=trip
    )


# ---------------- CUSTOMER CONFIRMS QUOTE ----------------

@app.route("/quote/<int:request_id>/confirm", methods=["POST"])
def confirm_quote(request_id):

    conn = get_db()

    conn.execute("""
        UPDATE trip_requests
        SET status = ?
        WHERE id = ?
    """, (
        "Confirmed",
        request_id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("bookings"))


# ---------------- BOOKINGS ----------------

@app.route("/bookings")
def bookings():

    conn = get_db()

    bookings_data = conn.execute("""
        SELECT *
        FROM trip_requests
        WHERE status = 'Confirmed'
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "bookings.html",
        bookings=bookings_data
    )


# ---------------- PAYMENT STATUS ----------------

@app.route("/booking/payment/<int:request_id>", methods=["POST"])
def update_payment(request_id):

    payment_status = request.form.get(
        "payment_status",
        "Pending"
    ).strip()

    allowed_statuses = [
        "Pending",
        "Partially Paid",
        "Paid"
    ]

    if payment_status not in allowed_statuses:
        payment_status = "Pending"

    conn = get_db()

    conn.execute("""
        UPDATE trip_requests
        SET payment_status = ?
        WHERE id = ?
    """, (
        payment_status,
        request_id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("bookings"))


# ---------------- RUN LOCALLY ----------------

if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
