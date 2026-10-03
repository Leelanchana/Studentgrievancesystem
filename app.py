from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "student_grievance_secret"


# ---------------- DATABASE CONNECTION ----------------

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- CREATE TABLES ----------------

def create_tables():

    conn = get_db()
    cursor = conn.cursor()

    # Student table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)

    # Complaint table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            category TEXT,
            title TEXT,
            description TEXT,
            location TEXT,
            status TEXT DEFAULT 'Pending',
            resolution TEXT DEFAULT 'Not yet provided',
            date_submitted TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Admin table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    # Create default admin
    cursor.execute("""
        INSERT OR IGNORE INTO admins(username, password)
        VALUES ('admin', 'admin123')
    """)

    conn.commit()
    conn.close()


# ---------------- HOME PAGE ----------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------- STUDENT REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        student_id = request.form["student_id"]
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()

        try:

            conn.execute("""
                INSERT INTO students
                (student_id, name, email, password)
                VALUES (?, ?, ?, ?)
            """, (student_id, name, email, password))

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()

            return "Student ID or Email already exists!"

        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        student_id = request.form["student_id"]
        password = request.form["password"]

        conn = get_db()

        student = conn.execute("""
            SELECT * FROM students
            WHERE student_id = ? AND password = ?
        """, (student_id, password)).fetchone()

        conn.close()

        if student:

            session["student_id"] = student["student_id"]
            session["student_name"] = student["name"]

            return redirect(url_for("student_dashboard"))

        return "Invalid Student ID or Password!"

    return render_template("login.html")


# ---------------- STUDENT DASHBOARD ----------------

@app.route("/student_dashboard")
def student_dashboard():

    if "student_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "student_dashboard.html",
        name=session["student_name"]
    )


# ---------------- SUBMIT COMPLAINT ----------------

@app.route("/submit_complaint", methods=["GET", "POST"])
def submit_complaint():

    if "student_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        category = request.form["category"]
        title = request.form["title"]
        description = request.form["description"]
        location = request.form["location"]

        conn = get_db()

        conn.execute("""
            INSERT INTO complaints
            (student_id, category, title, description, location)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session["student_id"],
            category,
            title,
            description,
            location
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("my_complaints"))

    return render_template("submit_complaint.html")


# ---------------- MY COMPLAINTS ----------------

@app.route("/my_complaints")
def my_complaints():

    if "student_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    complaints = conn.execute("""
        SELECT * FROM complaints
        WHERE student_id = ?
        ORDER BY date_submitted DESC
    """, (session["student_id"],)).fetchall()

    conn.close()

    return render_template(
        "my_complaints.html",
        complaints=complaints
    )


# ---------------- COMPLAINT DETAILS ----------------

@app.route("/complaint/<int:id>")
def complaint_details(id):

    if "student_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    complaint = conn.execute("""
        SELECT * FROM complaints
        WHERE id = ? AND student_id = ?
    """, (id, session["student_id"])).fetchone()

    conn.close()

    return render_template(
        "complaint_details.html",
        complaint=complaint
    )


# ---------------- ADMIN LOGIN ----------------

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()

        admin = conn.execute("""
            SELECT * FROM admins
            WHERE username = ? AND password = ?
        """, (username, password)).fetchone()

        conn.close()

        if admin:

            session["admin"] = username

            return redirect(url_for("admin_dashboard"))

        return "Invalid Admin Username or Password!"

    return render_template("admin_login.html")


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin_dashboard")
def admin_dashboard():

    if "admin" not in session:
        return redirect(url_for("admin_login"))

    category = request.args.get("category")

    conn = get_db()

    if category:
        complaints = conn.execute("""
            SELECT * FROM complaints
            WHERE category = ?
            ORDER BY date_submitted DESC
        """, (category,)).fetchall()
    else:
        complaints = conn.execute("""
            SELECT * FROM complaints
            ORDER BY date_submitted DESC
        """).fetchall()

    total_complaints = conn.execute("""
        SELECT COUNT(*) FROM complaints
    """).fetchone()[0]

    pending = conn.execute("""
        SELECT COUNT(*) FROM complaints
        WHERE status = 'Pending'
    """).fetchone()[0]

    in_progress = conn.execute("""
        SELECT COUNT(*) FROM complaints
        WHERE status = 'In Progress'
    """).fetchone()[0]

    resolved = conn.execute("""
        SELECT COUNT(*) FROM complaints
        WHERE status = 'Resolved'
    """).fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        complaints=complaints,
        selected_category=category,
        total_complaints=total_complaints,
        pending=pending,
        in_progress=in_progress,
        resolved=resolved
    )
    # ---------------- UPDATE COMPLAINT ----------------

@app.route("/update_complaint/<int:id>", methods=["POST"])
def update_complaint(id):

    if "admin" not in session:
        return redirect(url_for("admin_login"))

    status = request.form["status"]
    resolution = request.form["resolution"]

    conn = get_db()

    conn.execute("""
        UPDATE complaints
        SET status = ?, resolution = ?
        WHERE id = ?
    """, (status, resolution, id))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))
# ---------------- DELETE COMPLAINT ----------------

@app.route("/delete_complaint/<int:id>")
def delete_complaint(id):

    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db()

    conn.execute("""
        DELETE FROM complaints
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("index"))


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":

    create_tables()

    app.run(debug=True)