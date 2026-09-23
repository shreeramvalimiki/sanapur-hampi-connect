from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)


# --------------------------------------------------
# DATABASE SETUP
# --------------------------------------------------

def create_database():

    connection = sqlite3.connect("requests.db")

    connection.execute("""
        CREATE TABLE IF NOT EXISTS trip_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            travel_date TEXT,
            people INTEGER,
            services TEXT,
            preferred_time TEXT,
            message TEXT,
            status TEXT DEFAULT 'Pending',
            quote_amount TEXT DEFAULT '',
            payment_status TEXT DEFAULT 'Pending'
        )
    """)

    columns = [
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(trip_requests)"
        )
    ]

    # Add status if old database doesn't have it
    if "status" not in columns:

        connection.execute("""
            ALTER TABLE trip_requests
            ADD COLUMN status TEXT DEFAULT 'Pending'
        """)

    # Add quote amount if old database doesn't have it
    if "quote_amount" not in columns:

        connection.execute("""
            ALTER TABLE trip_requests
            ADD COLUMN quote_amount TEXT DEFAULT ''
        """)

    # Add payment status if old database doesn't have it
    if "payment_status" not in columns:

        connection.execute("""
            ALTER TABLE trip_requests
            ADD COLUMN payment_status TEXT DEFAULT 'Pending'
        """)

    connection.commit()
    connection.close()


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.route("/")
def home():

    return render_template("index.html")


# --------------------------------------------------
# PLAN YOUR TRIP
# --------------------------------------------------

@app.route("/plan", methods=["GET", "POST"])
def plan():

    if request.method == "POST":

        name = request.form["name"]

        phone = request.form["phone"]

        travel_date = request.form["travel_date"]

        people = request.form["people"]

        services = request.form.getlist("services")

        services_text = ", ".join(services)

        preferred_time = request.form["preferred_time"]

        message = request.form["message"]


        connection = sqlite3.connect("requests.db")

        connection.execute("""
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
            services_text,
            preferred_time,
            message,
            "Pending",
            "",
            "Pending"
        ))

        connection.commit()

        connection.close()


        return """
        <h1>Request Received! 🎉</h1>

        <p>
            Thank you!
            We will check availability and contact you.
        </p>

        <a href="/">
            Back to Home
        </a>
        """


    return render_template("plan.html")


# --------------------------------------------------
# ADMIN DASHBOARD
# --------------------------------------------------

@app.route("/admin")
def admin():

    connection = sqlite3.connect("requests.db")

    connection.row_factory = sqlite3.Row


    requests = connection.execute("""
        SELECT *
        FROM trip_requests
        ORDER BY id DESC
    """).fetchall()


    connection.close()


    total = len(requests)

    pending = sum(
        1 for r in requests
        if r["status"] == "Pending"
    )

    quoted = sum(
        1 for r in requests
        if r["status"] == "Quote Sent"
    )

    confirmed = sum(
        1 for r in requests
        if r["status"] == "Confirmed"
    )


    return render_template(
        "admin.html",
        requests=requests,
        total=total,
        pending=pending,
        quoted=quoted,
        confirmed=confirmed
    )


# --------------------------------------------------
# UPDATE REQUEST / SEND QUOTE
# --------------------------------------------------

@app.route(
    "/admin/update/<int:request_id>",
    methods=["POST"]
)
def update_request(request_id):

    quote_amount = request.form["quote_amount"]

    status = request.form["status"]


    connection = sqlite3.connect("requests.db")


    connection.execute("""
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


    connection.commit()

    connection.close()


    return redirect("/admin")


# --------------------------------------------------
# CUSTOMER QUOTE PAGE
# --------------------------------------------------

@app.route("/quote/<int:request_id>")
def quote(request_id):

    connection = sqlite3.connect("requests.db")

    connection.row_factory = sqlite3.Row


    customer = connection.execute("""
        SELECT *
        FROM trip_requests

        WHERE id = ?
    """, (
        request_id,
    )).fetchone()


    connection.close()


    if customer is None:

        return "Quote not found", 404


    return render_template(
        "quote.html",
        customer=customer
    )


# --------------------------------------------------
# CUSTOMER CONFIRMS BOOKING
# --------------------------------------------------

@app.route(
    "/quote/<int:request_id>/confirm",
    methods=["POST"]
)
def confirm_quote(request_id):

    connection = sqlite3.connect("requests.db")


    connection.execute("""
        UPDATE trip_requests

        SET
            status = 'Confirmed'

        WHERE id = ?
    """, (
        request_id,
    ))


    connection.commit()

    connection.close()


    return redirect(
        f"/quote/{request_id}"
    )


# --------------------------------------------------
# BOOKINGS PAGE
# --------------------------------------------------

@app.route("/bookings")
def bookings():

    connection = sqlite3.connect("requests.db")

    connection.row_factory = sqlite3.Row


    bookings = connection.execute("""
        SELECT *
        FROM trip_requests

        WHERE status = 'Confirmed'

        ORDER BY id DESC
    """).fetchall()


    connection.close()


    return render_template(
        "bookings.html",
        bookings=bookings
    )


# --------------------------------------------------
# UPDATE PAYMENT STATUS
# --------------------------------------------------

@app.route(
    "/booking/payment/<int:request_id>",
    methods=["POST"]
)
def update_payment(request_id):

    payment_status = request.form["payment_status"]


    connection = sqlite3.connect("requests.db")


    connection.execute("""
        UPDATE trip_requests

        SET payment_status = ?

        WHERE id = ?
    """, (
        payment_status,
        request_id
    ))


    connection.commit()

    connection.close()


    return redirect("/bookings")


# --------------------------------------------------
# START APPLICATION
# --------------------------------------------------

if __name__ == "__main__":

    create_database()

    app.run(debug=True)