from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

# =========================================================
# DATABASE
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "requests.db")


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_database():
    conn = get_db()
    cursor = conn.cursor()

    # Create the main table if it does not already exist
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
    conn.close()


def ensure_database():
    """
    Makes sure the database and table exist.
    This is called before database operations.
    """
    conn = get_db()

    conn.execute("""
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
    conn.close()


# Create database when Render/Gunicorn starts
create_database()


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# PLAN MY TRIP
# =========================================================

@app.route("/plan", methods=["GET", "POST"])
def plan():

    if request.method == "POST":

        # Make absolutely sure the table exists
        ensure_database()

        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        travel_date = request.form.get("travel_date", "").strip()
        people_text = request.form.get("people", "1").strip()

        services_list = request.form.getlist("services")
        services = ", ".join(services_list)

        preferred_time = request.form.get(
            "preferred_time", ""
        ).strip()

        message = request.form.get(
            "message", ""
        ).strip()

        # Required fields
        if not name:
            return "Please enter your name.", 400

        if not phone:
            return "Please enter your WhatsApp number.", 400

        if not travel_date:
            return "Please select your travel date.", 400

        try:
            people = int(people_text)
        except (ValueError, TypeError):
            people = 1

        if people < 1:
            people = 1

        # Save request
        conn = get_db()

        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO trip_requests (
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

        # Go to quote page
        return redirect(
            url_for(
                "quote",
                request_id=request_id
            )
        )

    return render_template("plan.html")


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
def admin():

    ensure_database()

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


# =========================================================
# UPDATE ADMIN REQUEST
# =========================================================

@app.route(
    "/admin/update/<int:request_id>",
    methods=["POST"]
)
def update_request(request_id):

    ensure_database()

    quote_amount = request.form.get(
        "quote_amount",
        "0"
    ).strip()

    status = request.form.get(
        "status",
        "New"
    ).strip()

    try:
        quote_amount = float(quote_amount)
    except (ValueError, TypeError):
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


# =========================================================
# QUOTE PAGE
# =========================================================

@app.route("/quote/<int:request_id>")
def quote(request_id):

    ensure_database()

    conn = get_db()

    trip = conn.execute("""
        SELECT *
        FROM trip_requests
        WHERE id = ?
    """, (
        request_id,
    )).fetchone()

    conn.close()

    if trip is None:
        return "Booking request not found.", 404

    return render_template(
        "quote.html",
        trip=trip
    )


# =========================================================
# CONFIRM QUOTE
# =========================================================

@app.route(
    "/quote/<int:request_id>/confirm",
    methods=["POST"]
)
def confirm_quote(request_id):

    ensure_database()

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


# =========================================================
# CONFIRMED BOOKINGS
# =========================================================

@app.route("/bookings")
def bookings():

    ensure_database()

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


# =========================================================
# PAYMENT STATUS
# =========================================================

@app.route(
    "/booking/payment/<int:request_id>",
    methods=["POST"]
)
def update_payment(request_id):

    ensure_database()

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


# =========================================================
# RUN LOCALLY
# =========================================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
