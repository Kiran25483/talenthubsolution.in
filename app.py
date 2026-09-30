from flask import Flask, render_template, request, redirect, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "talenthub-secret-key"

DB = "consultancy.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            experience TEXT,
            salary TEXT,
            category TEXT,
            description TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            skills TEXT,
            experience TEXT,
            resume TEXT,
            job_id INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS employer_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            contact_person TEXT,
            email TEXT,
            phone TEXT,
            job_title TEXT,
            openings INTEGER,
            description TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            message TEXT
        )
    """)

    # Add sample jobs only if table is empty
    count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    if count == 0:
        jobs = [
            (
                "Python AI Engineer",
                "Confidential Client",
                "Noida",
                "2-5 Years",
                "₹8-15 LPA",
                "IT",
                "Develop AI, GenAI and Python-based applications."
            ),
            (
                "Software Developer",
                "Confidential Client",
                "Bangalore",
                "2-4 Years",
                "₹6-12 LPA",
                "IT",
                "Develop and maintain web applications."
            ),
            (
                "HR Executive",
                "Confidential Client",
                "Delhi NCR",
                "1-3 Years",
                "₹3-6 LPA",
                "HR",
                "Manage recruitment and employee coordination."
            ),
            (
                "Business Development Executive",
                "Confidential Client",
                "Noida",
                "1-4 Years",
                "₹3-7 LPA",
                "Sales",
                "Generate leads and manage client relationships."
            )
        ]

        conn.executemany("""
            INSERT INTO jobs
            (title, company, location, experience, salary, category, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, jobs)

    conn.commit()
    conn.close()


@app.route("/")
def home():
    conn = get_db()
    jobs = conn.execute(
        "SELECT * FROM jobs ORDER BY id DESC LIMIT 6"
    ).fetchall()
    conn.close()

    return render_template("index.html", jobs=jobs)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/services")
def services():
    return render_template("services.html")


@app.route("/jobs")
def jobs():
    conn = get_db()
    jobs = conn.execute(
        "SELECT * FROM jobs ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return render_template("jobs.html", jobs=jobs)


@app.route("/employers", methods=["GET", "POST"])
def employers():

    if request.method == "POST":

        company = request.form.get("company")
        contact_person = request.form.get("contact_person")
        email = request.form.get("email")
        phone = request.form.get("phone")
        job_title = request.form.get("job_title")
        openings = request.form.get("openings")
        description = request.form.get("description")

        conn = get_db()

        conn.execute("""
            INSERT INTO employer_requests
            (company, contact_person, email, phone, job_title, openings, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            company,
            contact_person,
            email,
            phone,
            job_title,
            openings,
            description
        ))

        conn.commit()
        conn.close()

        flash("Your hiring requirement has been submitted successfully.")

        return redirect("/employers")

    return render_template("employers.html")


@app.route("/candidates", methods=["GET", "POST"])
def candidates():

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        skills = request.form.get("skills")
        experience = request.form.get("experience")
        resume = request.form.get("resume")
        job_id = request.form.get("job_id")

        conn = get_db()

        conn.execute("""
            INSERT INTO applications
            (name, email, phone, skills, experience, resume, job_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            email,
            phone,
            skills,
            experience,
            resume,
            job_id
        ))

        conn.commit()
        conn.close()

        flash("Your application has been submitted successfully.")

        return redirect("/candidates")

    return render_template("candidates.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        message = request.form.get("message")

        conn = get_db()

        conn.execute("""
            INSERT INTO contact_messages
            (name, email, phone, message)
            VALUES (?, ?, ?, ?)
        """, (
            name,
            email,
            phone,
            message
        ))

        conn.commit()
        conn.close()

        flash("Thank you. We will contact you soon.")

        return redirect("/contact")

    return render_template("contact.html")


gunicorn app:app