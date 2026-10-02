import os
import hmac
import secrets
import sqlite3
import uuid

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    flash,
    session,
    url_for,
    abort,
    send_from_directory
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename


# ============================================================
# FLASK CONFIGURATION
# ============================================================

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

DB = "consultancy.db"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().casefold()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

BLOG_POSTS = [
    {
        "slug": "build-a-resume-recruiters-can-scan",
        "category": "Career toolkit",
        "read_time": "4 min read",
        "title": "Build a resume recruiters can scan",
        "excerpt": "Make the most relevant parts of your experience easy to find, understand, and verify.",
        "sections": [
            {
                "heading": "Start with the role in mind",
                "body": "Read the job description and identify the skills it emphasizes. Bring your closest matching experience forward, while keeping every detail accurate."
            },
            {
                "heading": "Show evidence, not just keywords",
                "body": "Describe what you worked on, how you contributed, and what changed as a result. Use numbers only when you can confidently explain them."
            },
            {
                "heading": "Keep the layout easy to follow",
                "body": "Use clear section headings, consistent dates, and concise bullet points. Check the final document on both a phone and a desktop before sending it."
            }
        ]
    },
    {
        "slug": "prepare-for-an-interview-with-confidence",
        "category": "Interview preparation",
        "read_time": "5 min read",
        "title": "Prepare for an interview with confidence",
        "excerpt": "A simple preparation routine helps you explain your experience clearly and ask better questions.",
        "sections": [
            {
                "heading": "Connect your experience to the role",
                "body": "Choose a few examples that show the skills the role requires. Be ready to explain the situation, your actions, and the outcome in your own words."
            },
            {
                "heading": "Practice out loud",
                "body": "Rehearse concise answers to common questions, but avoid memorizing a script. A natural explanation is easier to adapt when the conversation changes direction."
            },
            {
                "heading": "Prepare thoughtful questions",
                "body": "Ask about the team's priorities, how success is evaluated, and what the next steps in the process look like."
            }
        ]
    },
    {
        "slug": "choose-training-that-moves-you-forward",
        "category": "Training & development",
        "read_time": "4 min read",
        "title": "Choose training that moves you forward",
        "excerpt": "Focus your learning on a real target role, then build practical evidence of the skills you gain.",
        "sections": [
            {
                "heading": "Pick a realistic role target",
                "body": "Review several job descriptions for the role you want. Note the skills that appear repeatedly and compare them with what you already know."
            },
            {
                "heading": "Learn by doing",
                "body": "Pair lessons with exercises or small projects. Practical work helps you test your understanding and gives you specific examples to discuss with employers."
            },
            {
                "heading": "Make a plan for the next step",
                "body": "Update your resume with skills you can demonstrate, practice explaining your work, and apply to opportunities that match your current experience."
            }
        ]
    }
]


# ============================================================
# UPLOAD CONFIGURATION
# ============================================================

UPLOAD_FOLDER = os.environ.get(
    "RESUME_UPLOAD_FOLDER",
    os.path.join(app.instance_path, "uploads", "resumes")
)

LEGACY_UPLOAD_FOLDER = os.path.join(
    app.static_folder,
    "uploads",
    "resumes"
)

PROFILE_PHOTO_UPLOAD_FOLDER = os.environ.get(
    "PROFILE_PHOTO_UPLOAD_FOLDER",
    os.path.join(app.instance_path, "uploads", "profile_photos")
)

ALLOWED_EXTENSIONS = {
    "pdf",
    "doc",
    "docx"
}

ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_PROFILE_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["LEGACY_UPLOAD_FOLDER"] = LEGACY_UPLOAD_FOLDER
app.config["PROFILE_PHOTO_UPLOAD_FOLDER"] = PROFILE_PHOTO_UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROFILE_PHOTO_UPLOAD_FOLDER, exist_ok=True)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():

    conn = sqlite3.connect(DB)

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# CHECK ALLOWED RESUME FILE
# ============================================================

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def allowed_profile_photo(upload):

    if not upload or not upload.filename or "." not in upload.filename:
        return False

    extension = upload.filename.rsplit(".", 1)[1].lower()

    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return False

    upload.stream.seek(0, os.SEEK_END)
    photo_size = upload.stream.tell()
    upload.stream.seek(0)

    if photo_size > MAX_PROFILE_PHOTO_SIZE:
        return False

    header = upload.stream.read(12)
    upload.stream.seek(0)

    if extension in {"jpg", "jpeg"}:
        return header.startswith(b"\xff\xd8\xff")

    if extension == "png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")

    return header.startswith(b"RIFF") and header[8:12] == b"WEBP"


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():

    conn = get_db()


    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT NOT NULL UNIQUE,

            phone TEXT,

            password TEXT NOT NULL,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP

        )
    """)

    user_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(users)")
    }

    if "profile_photo" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN profile_photo TEXT")


    # --------------------------------------------------------
    # JOBS
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # APPLICATIONS
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT NOT NULL,

            phone TEXT,

            skills TEXT,

            experience TEXT,

            resume TEXT,

            job_id INTEGER,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP

        )
    """)


    # --------------------------------------------------------
    # EMPLOYER REQUESTS
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS employer_requests (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            company TEXT NOT NULL,

            contact_person TEXT,

            email TEXT,

            phone TEXT,

            job_title TEXT,

            openings INTEGER,

            description TEXT,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP

        )
    """)


    # --------------------------------------------------------
    # CONTACT MESSAGES
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS contact_messages (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT,

            email TEXT,

            phone TEXT,

            message TEXT,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP

        )
    """)


    # ========================================================
    # DEFAULT JOBS
    # ========================================================

    count = conn.execute(
        "SELECT COUNT(*) FROM jobs"
    ).fetchone()[0]


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
            (
                title,
                company,
                location,
                experience,
                salary,
                category,
                description
            )

            VALUES (?, ?, ?, ?, ?, ?, ?)

        """, jobs)


    conn.commit()

    conn.close()


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    conn = get_db()

    jobs = conn.execute("""
        SELECT *
        FROM jobs
        ORDER BY id DESC
        LIMIT 6
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        jobs=jobs
    )


# ============================================================
# ABOUT
# ============================================================

@app.route("/about")
def about():

    return render_template(
        "about.html",
        featured_posts=BLOG_POSTS[:2]
    )


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))

    admin_configured = bool(ADMIN_EMAIL and ADMIN_PASSWORD)

    if request.method == "POST":

        if not admin_configured:
            flash("Staff access has not been configured on the server.", "warning")

        else:
            submitted_email = request.form.get("email", "").strip().casefold()
            submitted_password = request.form.get("password", "")
            email_matches = hmac.compare_digest(submitted_email, ADMIN_EMAIL)
            password_matches = hmac.compare_digest(submitted_password, ADMIN_PASSWORD)

            if email_matches and password_matches:
                session.clear()
                session["is_admin"] = True
                return redirect(url_for("admin_dashboard"))

            flash("Invalid staff email or password.", "danger")

    return render_template(
        "admin_login.html",
        admin_configured=admin_configured
    )

@app.route("/admin")
def admin_dashboard():

    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    conn = get_db()
    applicants = conn.execute("""
        SELECT
            applications.id,
            applications.name,
            applications.email,
            applications.phone,
            applications.skills,
            applications.experience,
            applications.resume,
            applications.created_at,
            jobs.title AS job_title,
            users.id AS user_id,
            users.profile_photo
        FROM applications
        LEFT JOIN jobs ON jobs.id = applications.job_id
        LEFT JOIN users ON lower(users.email) = lower(applications.email)
        ORDER BY applications.id DESC
    """).fetchall()
    conn.close()

    return render_template(
        "admin_dashboard.html",
        applicants=applicants
    )


@app.route("/admin/logout")
def admin_logout():

    session.clear()
    flash("Staff session ended.", "success")
    return redirect(url_for("home"))

@app.route("/admin/applicants/<int:user_id>/photo")
def admin_candidate_photo(user_id):

    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    conn = get_db()
    user = conn.execute(
        "SELECT profile_photo FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    if not user or not user["profile_photo"]:
        abort(404)

    return send_from_directory(
        app.config["PROFILE_PHOTO_UPLOAD_FOLDER"],
        user["profile_photo"]
    )

@app.route("/applications/<int:application_id>/resume")
def application_resume(application_id):

    if not session.get("is_admin") and "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    application = conn.execute(
        "SELECT email, resume FROM applications WHERE id = ?",
        (application_id,)
    ).fetchone()
    conn.close()

    if not application or not application["resume"]:
        abort(404)

    if not session.get("is_admin") and application["email"].casefold() != session.get("user_email", "").casefold():
        abort(403)

    filename = application["resume"]
    resume_folder = app.config["UPLOAD_FOLDER"]

    if not os.path.isfile(os.path.join(resume_folder, filename)):
        resume_folder = app.config["LEGACY_UPLOAD_FOLDER"]

    if not os.path.isfile(os.path.join(resume_folder, filename)):
        abort(404)

    return send_from_directory(resume_folder, filename, as_attachment=True)

@app.route("/profile/photo")
def candidate_profile_photo():

    if "user_id" not in session:
        abort(403)

    conn = get_db()
    user = conn.execute(
        "SELECT profile_photo FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()
    conn.close()

    if not user or not user["profile_photo"]:
        abort(404)

    return send_from_directory(
        app.config["PROFILE_PHOTO_UPLOAD_FOLDER"],
        user["profile_photo"]
    )
def blog():

    return render_template(
        "blog.html",
        posts=BLOG_POSTS
    )


@app.route("/blog")
def blog():

    return render_template(
        "blog.html",
        posts=BLOG_POSTS
    )


@app.route("/blog/<slug>")
def blog_post(slug):

    post = next(
        (post for post in BLOG_POSTS if post["slug"] == slug),
        None
    )

    if post is None:
        abort(404)

    related_posts = [item for item in BLOG_POSTS if item != post]

    return render_template(
        "blog_post.html",
        post=post,
        related_posts=related_posts
    )


# ============================================================
# SERVICES
# ============================================================

@app.route("/services")
def services():

    return render_template("services.html")


# ============================================================
# JOBS
# ============================================================

@app.route("/jobs")
def jobs():

    search_query = request.args.get("q", "").strip()
    selected_category = request.args.get("category", "").strip()
    selected_location = request.args.get("location", "").strip()
    filters = []
    parameters = []

    if search_query:
        filters.append("""(
            instr(lower(title), lower(?)) > 0
            OR instr(lower(company), lower(?)) > 0
            OR instr(lower(description), lower(?)) > 0
        )""")
        parameters.extend([search_query] * 3)

    if selected_category:
        filters.append("category = ?")
        parameters.append(selected_category)

    if selected_location:
        filters.append("instr(lower(location), lower(?)) > 0")
        parameters.append(selected_location)

    query = "SELECT * FROM jobs"

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY id DESC"

    conn = get_db()

    jobs = conn.execute(query, parameters).fetchall()
    categories = conn.execute("""
        SELECT DISTINCT category
        FROM jobs
        WHERE category IS NOT NULL AND category != ''
        ORDER BY category
    """).fetchall()

    conn.close()

    return render_template(
        "jobs.html",
        jobs=jobs,
        categories=categories,
        search_query=search_query,
        selected_category=selected_category,
        selected_location=selected_location
    )


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not name or not email or not password:

            flash(
                "Please fill all required fields.",
                "danger"
            )

            return redirect(
                url_for("register")
            )


        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return redirect(
                url_for("register")
            )


        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "danger"
            )

            return redirect(
                url_for("register")
            )


        # ----------------------------------------------------
        # PASSWORD HASH
        # ----------------------------------------------------

        password_hash = generate_password_hash(
            password
        )


        # ----------------------------------------------------
        # SAVE USER
        # ----------------------------------------------------

        conn = get_db()

        try:

            conn.execute("""
                INSERT INTO users
                (
                    name,
                    email,
                    phone,
                    password
                )

                VALUES (?, ?, ?, ?)

            """, (
                name,
                email,
                phone,
                password_hash
            ))

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()

            flash(
                "An account with this email already exists.",
                "danger"
            )

            return redirect(
                url_for("register")
            )

        conn.close()


        flash(
            "Account created successfully. Please login.",
            "success"
        )

        return redirect(
            url_for("login")
        )


    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )


        conn = get_db()

        user = conn.execute("""
            SELECT *
            FROM users
            WHERE email = ?

        """, (email,)).fetchone()

        conn.close()


        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]

            session["user_name"] = user["name"]

            session["user_email"] = user["email"]


            flash(
                "Login successful!",
                "success"
            )

            pending_job_id = session.pop("pending_job_id", None)

            if pending_job_id:
                return redirect(
                    url_for("candidates", job_id=pending_job_id)
                )

            return redirect(
                url_for("dashboard")
            )


        flash(
            "Invalid email or password.",
            "danger"
        )


    return render_template(
        "login.html"
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(
            url_for("login")
        )


    conn = get_db()


    # Get user
    user = conn.execute("""
        SELECT *
        FROM users
        WHERE id = ?

    """, (
        session["user_id"],
    )).fetchone()


    # Get user's applications
    applications = conn.execute("""
        SELECT applications.*, jobs.title AS job_title
        FROM applications
        LEFT JOIN jobs ON jobs.id = applications.job_id
        WHERE applications.email = ?
        ORDER BY applications.id DESC

    """, (
        session["user_email"],
    )).fetchall()


    conn.close()


    if not user:

        session.clear()

        flash(
            "User account was not found.",
            "danger"
        )

        return redirect(
            url_for("login")
        )


    return render_template(
        "dashboard.html",
        user=user,
        applications=applications
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out successfully.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# ============================================================
# EMPLOYERS
# ============================================================

@app.route("/employers", methods=["GET", "POST"])
def employers():

    if request.method == "POST":

        company = request.form.get(
            "company",
            ""
        ).strip()

        contact_person = request.form.get(
            "contact_person",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        job_title = request.form.get(
            "job_title",
            ""
        ).strip()

        openings = request.form.get(
            "openings",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()


        conn = get_db()

        conn.execute("""
            INSERT INTO employer_requests
            (
                company,
                contact_person,
                email,
                phone,
                job_title,
                openings,
                description
            )

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


        flash(
            "Your hiring requirement has been submitted successfully.",
            "success"
        )

        return redirect(
            url_for("employers")
        )


    return render_template(
        "employers.html"
    )


# ============================================================
# CANDIDATE APPLICATION
# ============================================================

@app.route("/candidates", methods=["GET", "POST"])
def candidates():

    selected_job_id = request.args.get("job_id", type=int)

    # --------------------------------------------------------
    # LOGIN REQUIRED
    # --------------------------------------------------------

    if "user_id" not in session:

        if selected_job_id:
            session["pending_job_id"] = selected_job_id

        flash(
            "Please login or create an account before submitting your resume.",
            "warning"
        )

        return redirect(
            url_for("login")
        )


    if request.method == "POST":

        name = session.get(
            "user_name",
            request.form.get("name", "")
        ).strip()

        email = session.get(
            "user_email",
            request.form.get("email", "")
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        skills = request.form.get(
            "skills",
            ""
        ).strip()

        experience = request.form.get(
            "experience",
            ""
        ).strip()

        job_id = request.form.get(
            "job_id",
            type=int
        )


        # ----------------------------------------------------
        # RESUME
        # ----------------------------------------------------

        resume = request.files.get(
            "resume"
        )


        if not resume or resume.filename == "":

            flash(
                "Please upload your resume.",
                "danger"
            )

            return redirect(
                url_for("candidates")
            )


        # ----------------------------------------------------
        # CHECK FILE TYPE
        # ----------------------------------------------------

        if not allowed_file(
            resume.filename
        ):

            flash(
                "Only PDF, DOC and DOCX files are allowed.",
                "danger"
            )

            return redirect(
                url_for("candidates")
            )

        profile_photo = request.files.get("profile_photo")
        has_profile_photo = bool(profile_photo and profile_photo.filename)

        if has_profile_photo and not allowed_profile_photo(profile_photo):
            flash("Profile photos must be valid JPG, PNG, or WebP images under 5 MB.", "danger")
            return redirect(
                url_for("candidates", job_id=job_id) if job_id else url_for("candidates")
            )


        # ----------------------------------------------------
        # CREATE UNIQUE FILE NAME
        # ----------------------------------------------------

        original_filename = secure_filename(
            resume.filename
        )

        extension = original_filename.rsplit(
            ".",
            1
        )[1].lower()


        unique_filename = (
            str(uuid.uuid4())
            + "."
            + extension
        )


        # ----------------------------------------------------
        # SAVE FILE
        # ----------------------------------------------------

        resume_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
        resume.save(resume_path)

        profile_photo_filename = None

        if has_profile_photo:
            photo_extension = secure_filename(profile_photo.filename).rsplit(".", 1)[1].lower()
            profile_photo_filename = str(uuid.uuid4()) + "." + photo_extension
            profile_photo.save(os.path.join(
                app.config["PROFILE_PHOTO_UPLOAD_FOLDER"],
                profile_photo_filename
            ))


        # ----------------------------------------------------
        # SAVE APPLICATION TO DATABASE
        # ----------------------------------------------------

        conn = get_db()

        if profile_photo_filename:
            conn.execute(
                "UPDATE users SET profile_photo = ? WHERE id = ?",
                (profile_photo_filename, session["user_id"])
            )

        conn.execute("""
            INSERT INTO applications
            (
                name,
                email,
                phone,
                skills,
                experience,
                resume,
                job_id
            )

            VALUES (?, ?, ?, ?, ?, ?, ?)

        """, (
            name,
            email,
            phone,
            skills,
            experience,
            unique_filename,
            job_id
        ))


        conn.commit()

        conn.close()


        flash(
            "Your application and resume have been submitted successfully.",
            "success"
        )

        return redirect(
            url_for("dashboard")
        )


    conn = get_db()
    user = conn.execute(
        "SELECT profile_photo FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()
    conn.close()

    return render_template(
        "candidates.html",
        selected_job_id=selected_job_id,
        profile_photo=user["profile_photo"] if user else None
    )


# ============================================================
# CONTACT
# ============================================================

@app.route("/contact", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        message = request.form.get(
            "message",
            ""
        ).strip()


        conn = get_db()

        conn.execute("""
            INSERT INTO contact_messages
            (
                name,
                email,
                phone,
                message
            )

            VALUES (?, ?, ?, ?)

        """, (
            name,
            email,
            phone,
            message
        ))


        conn.commit()

        conn.close()


        flash(
            "Thank you. We will contact you soon.",
            "success"
        )

        return redirect(
            url_for("contact")
        )


    return render_template(
        "contact.html"
    )


# ============================================================
# START APPLICATION
# ============================================================

init_db()


if __name__ == "__main__":

    app.run(
        debug=True
    )