"""
ONLINE COURSE REGISTRATION SYSTEM
One-file beginner-friendly version.
Requirements: Python 3.10+ (no extra packages required)
Database: SQLite (created automatically)
Run: python app.py
Then open: http://127.0.0.1:5000

This uses Python's built-in HTTP server and SQLite so there is no MySQL/Tomcat setup.
For production, use a proper web framework, CSRF protection, and deployment hardening.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
import sqlite3
import hashlib
import hmac
import secrets
import html
import os
import threading
import webbrowser
import time

HOST = "127.0.0.1"
PORT = 5000
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "course_registration.db")
SESSIONS = {}
SESSION_LOCK = threading.Lock()

COURSE_SEED = [
    ("Python Programming", "3 Months", 5000.00),
    ("Web Development", "4 Months", 7000.00),
    ("Java Programming", "3 Months", 6000.00),
    ("Data Science", "6 Months", 10000.00),
]

def db():
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name TEXT NOT NULL UNIQUE,
            duration TEXT NOT NULL,
            fees REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            registration_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, course_id),
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        """)
        for name, duration, fees in COURSE_SEED:
            con.execute(
                "INSERT OR IGNORE INTO courses(course_name, duration, fees) VALUES (?, ?, ?)",
                (name, duration, fees),
            )

def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240_000)
    return salt.hex() + "$" + digest.hex()

def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        candidate = hash_password(password, bytes.fromhex(salt_hex)).split("$", 1)[1]
        return hmac.compare_digest(candidate, digest_hex)
    except (ValueError, TypeError):
        return False

def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)

def page(title, body, user=None, message=None, error=False):
    nav_user = (
        f'<span class="welcome">Hi, {esc(user["name"])}</span>'
        '<a href="/courses">Courses</a><a href="/dashboard">My Dashboard</a>'
        '<form class="navform" method="post" action="/logout"><button class="linkbtn">Logout</button></form>'
        if user else
        '<a href="/login">Login</a><a class="navcta" href="/register">Register</a>'
    )
    notice = ""
    if message:
        notice = f'<div class="notice {"error" if error else ""}">{esc(message)}</div>'
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | CourseConnect</title>
<style>
:root{{--ink:#20243a;--purple:#4f46e5;--purple2:#7c3aed;--bg:#f4f6ff;--muted:#68708a;--line:#e5e7ef}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif}}
nav{{display:flex;align-items:center;justify-content:space-between;padding:16px max(5%,calc((100% - 1080px)/2));background:#28245f;color:white;gap:14px;flex-wrap:wrap}}
.brand{{font-weight:800;font-size:20px;color:white;text-decoration:none}} .navlinks{{display:flex;align-items:center;gap:16px;flex-wrap:wrap}}
nav a,.linkbtn{{color:white;text-decoration:none;font-weight:600;font-size:14px}} .welcome{{font-size:14px;color:#e0e7ff}}
.navcta{{background:white;color:#3730a3!important;padding:9px 14px;border-radius:9px}}
.navform{{display:inline;margin:0}} .linkbtn{{border:0;background:transparent;cursor:pointer;padding:0}}
main{{width:min(1080px,92%);margin:34px auto 70px}} .hero{{padding:54px 42px;border-radius:24px;background:linear-gradient(125deg,#4338ca,#7c3aed);color:white;box-shadow:0 16px 40px #4f46e52b}}
.hero h1{{font-size:clamp(32px,5vw,52px);line-height:1.08;margin:0 0 16px}} .hero p{{font-size:17px;line-height:1.7;max-width:650px;color:#ede9fe}}
.btn,button{{border:0;display:inline-block;background:var(--purple);color:white;border-radius:10px;padding:12px 17px;font-weight:700;text-decoration:none;cursor:pointer}}
.btn.white{{background:white;color:#4338ca;margin-right:8px}} .btn.ghost{{background:#ffffff20;color:white;border:1px solid #ffffff80}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:18px}}
.card{{background:white;border:1px solid var(--line);padding:24px;border-radius:17px;box-shadow:0 8px 25px #1e24400a;margin-bottom:18px}}
.card h2,.card h3{{margin-top:0}} .muted{{color:var(--muted)}} .tag{{display:inline-block;padding:6px 10px;background:#eef2ff;color:#4338ca;border-radius:20px;font-size:12px;font-weight:800}}
form.fieldform label{{display:block;font-size:14px;font-weight:700;margin:14px 0 6px}}
input{{width:100%;padding:12px 13px;border:1px solid #cfd4e3;border-radius:9px;font-size:15px;background:white}}
input:focus{{outline:2px solid #c7d2fe;border-color:var(--purple)}} .fieldform button{{width:100%;margin-top:18px}}
.notice{{padding:13px 15px;border-radius:10px;background:#dcfce7;color:#166534;margin:0 0 18px}} .notice.error{{background:#fee2e2;color:#991b1b}}
table{{width:100%;border-collapse:collapse;background:white}} th,td{{padding:13px;text-align:left;border-bottom:1px solid var(--line)}} th{{background:#eef2ff}}
.price{{font-size:26px;font-weight:800;color:#4338ca}} .footer{{text-align:center;padding:24px;color:var(--muted);font-size:13px}}
@media(max-width:600px){{.hero{{padding:34px 23px}}nav{{padding:16px 4%}}main{{margin-top:22px}}}}
</style></head><body>
<nav><a class="brand" href="/">CourseConnect</a><div class="navlinks">{nav_user}</div></nav>
<main>{notice}{body}</main><div class="footer">Online Course Registration System · Student Mini Project</div>
</body></html>"""

def current_user(handler):
    sid = handler.cookies.get("sid")
    if not sid:
        return None
    with SESSION_LOCK:
        student_id = SESSIONS.get(sid)
    if not student_id:
        return None
    with db() as con:
        row = con.execute("SELECT id, name, email FROM students WHERE id=?", (student_id,)).fetchone()
    return dict(row) if row else None

class App(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

    @property
    def cookies(self):
        raw = self.headers.get("Cookie", "")
        result = {}
        for part in raw.split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                result[k] = v
        return result

    def send_html(self, content, status=200, headers=None):
        data = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'")
        if headers:
            for k, v in headers:
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, path, headers=None):
        self.send_response(303)
        self.send_header("Location", path)
        if headers:
            for k, v in headers:
                self.send_header(k, v)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def read_form(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 100_000:
            raise ValueError("Form is too large.")
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        return {k: v[0] for k, v in parse_qs(raw, keep_blank_values=True).items()}

    def do_GET(self):
        parsed = urlparse(self.path)
        path, query = parsed.path, parse_qs(parsed.query)
        user = current_user(self)
        if path == "/":
            body = """
            <section class="hero">
              <span class="tag">STUDENT PORTAL</span>
              <h1>Learn something new.<br>Build your future.</h1>
              <p>Explore courses, register online, and manage your learning in one simple place.</p>
              <a class="btn white" href="/register">Create Student Account</a>
              <a class="btn ghost" href="/login">Student Login</a>
            </section>
            <h2 style="margin-top:32px">Everything you need to get started</h2>
            <div class="grid">
              <section class="card"><h3>📚 Explore Courses</h3><p class="muted">Check course duration and fees before enrolling.</p></section>
              <section class="card"><h3>📝 Quick Registration</h3><p class="muted">Register for courses using your student account.</p></section>
              <section class="card"><h3>📊 Student Dashboard</h3><p class="muted">See your enrolled courses and registration dates.</p></section>
            </div>"""
            return self.send_html(page("Home", body, user))
        if path == "/register":
            if user:
                return self.redirect("/courses")
            msg = None
            error = False
            if "error" in query:
                error = True
                msg = ("That email is already registered. Please log in."
                       if query["error"][0] == "exists" else
                       "Please enter a name, valid email and password of 8–72 characters.")
            body = """
            <section class="card" style="max-width:540px;margin:0 auto">
              <h1>Create your student account</h1><p class="muted">Fill in your details to get started.</p>
              <form class="fieldform" method="post" action="/register">
                <label for="name">Full name</label><input id="name" name="name" required maxlength="100" autocomplete="name">
                <label for="email">Email address</label><input id="email" name="email" type="email" required maxlength="254" autocomplete="email">
                <label for="password">Password (8–72 characters)</label><input id="password" name="password" type="password" required minlength="8" maxlength="72" autocomplete="new-password">
                <button type="submit">Create Account</button>
              </form><p class="muted">Already registered? <a href="/login">Log in</a></p>
            </section>"""
            return self.send_html(page("Register", body, user, msg, error))
        if path == "/login":
            if user:
                return self.redirect("/courses")
            msg = None
            error = False
            if "registered" in query:
                msg = "Account created successfully. Please log in."
            if "error" in query:
                msg, error = "Email or password is incorrect.", True
            body = """
            <section class="card" style="max-width:540px;margin:0 auto">
              <h1>Welcome back</h1><p class="muted">Log in to view and register for courses.</p>
              <form class="fieldform" method="post" action="/login">
                <label for="email">Email address</label><input id="email" name="email" type="email" required maxlength="254" autocomplete="email">
                <label for="password">Password</label><input id="password" name="password" type="password" required maxlength="72" autocomplete="current-password">
                <button type="submit">Login</button>
              </form><p class="muted">New student? <a href="/register">Create an account</a></p>
            </section>"""
            return self.send_html(page("Login", body, user, msg, error))
        if path == "/courses":
            if not user:
                return self.redirect("/login")
            with db() as con:
                courses = con.execute("SELECT id, course_name, duration, fees FROM courses ORDER BY id").fetchall()
            cards = ""
            for c in courses:
                cards += f"""
                <section class="card">
                  <span class="tag">{esc(c['duration'])}</span>
                  <h2 style="margin-top:14px">{esc(c['course_name'])}</h2>
                  <p class="muted">Course fee</p><div class="price">₹{c['fees']:,.2f}</div>
                  <form method="post" action="/enroll">
                    <input type="hidden" name="course_id" value="{c['id']}">
                    <button type="submit" style="margin-top:15px;width:100%">Register for Course</button>
                  </form>
                </section>"""
            body = f"<h1>Available Courses</h1><p class='muted'>Welcome, {esc(user['name'])}. Choose a course to register.</p><div class='grid'>{cards}</div>"
            return self.send_html(page("Courses", body, user))
        if path == "/dashboard":
            if not user:
                return self.redirect("/login")
            with db() as con:
                rows = con.execute("""
                    SELECT c.course_name, c.duration, c.fees, r.registration_date
                    FROM registrations r JOIN courses c ON c.id=r.course_id
                    WHERE r.student_id=? ORDER BY r.registration_date DESC
                """, (user["id"],)).fetchall()
            msg, error = None, False
            if "success" in query:
                msg = "Course registered successfully!"
            elif "duplicate" in query:
                msg = "You are already registered for that course."
                error = True
            elif "invalid" in query:
                msg = "Please choose a valid course."
                error = True
            if rows:
                trs = "".join(
                    f"<tr><td>{esc(r['course_name'])}</td><td>{esc(r['duration'])}</td>"
                    f"<td>₹{r['fees']:,.2f}</td><td>{esc(r['registration_date'])}</td></tr>"
                    for r in rows
                )
            else:
                trs = '<tr><td colspan="4">You have not registered for any courses yet.</td></tr>'
            body = f"""
            <h1>My Dashboard</h1><p class="muted">Welcome, {esc(user['name'])}. Here are your registrations.</p>
            <section class="card"><h2>My registered courses</h2>
            <div style="overflow-x:auto"><table><thead><tr><th>Course</th><th>Duration</th><th>Fees</th><th>Registered on</th></tr></thead>
            <tbody>{trs}</tbody></table></div>
            <p style="margin-top:22px"><a class="btn" href="/courses">Browse More Courses</a></p></section>"""
            return self.send_html(page("Dashboard", body, user, msg, error))
        if path == "/favicon.ico":
            self.send_response(204); self.end_headers(); return
        return self.send_html(page("Not Found", "<section class='card'><h1>Page not found</h1><a class='btn' href='/'>Go home</a></section>", user), 404)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = self.read_form()
        except ValueError:
            return self.send_html(page("Bad Request", "<section class='card'><h1>Request too large</h1></section>"), 413)

        if path == "/register":
            name = data.get("name", "").strip()
            email = data.get("email", "").strip().lower()
            password = data.get("password", "")
            if not name or len(name) > 100 or not email or len(email) > 254 or "@" not in email or len(password) < 8 or len(password) > 72:
                return self.redirect("/register?error=invalid")
            try:
                with db() as con:
                    con.execute("INSERT INTO students(name,email,password_hash) VALUES(?,?,?)",
                                (name, email, hash_password(password)))
            except sqlite3.IntegrityError:
                return self.redirect("/register?error=exists")
            return self.redirect("/login?registered=1")

        if path == "/login":
            email = data.get("email", "").strip().lower()
            password = data.get("password", "")
            with db() as con:
                row = con.execute("SELECT id,password_hash FROM students WHERE email=?", (email,)).fetchone()
            if not row or not verify_password(password, row["password_hash"]):
                return self.redirect("/login?error=1")
            sid = secrets.token_urlsafe(32)
            with SESSION_LOCK:
                SESSIONS[sid] = row["id"]
            return self.redirect("/courses", [("Set-Cookie", f"sid={sid}; HttpOnly; SameSite=Lax; Path=/")])

        if path == "/enroll":
            user = current_user(self)
            if not user:
                return self.redirect("/login")
            try:
                course_id = int(data.get("course_id", "0"))
            except ValueError:
                return self.redirect("/dashboard?invalid=1")
            with db() as con:
                exists = con.execute("SELECT id FROM courses WHERE id=?", (course_id,)).fetchone()
                if not exists:
                    return self.redirect("/dashboard?invalid=1")
                try:
                    con.execute("INSERT INTO registrations(student_id,course_id) VALUES(?,?)",
                                (user["id"], course_id))
                except sqlite3.IntegrityError:
                    return self.redirect("/dashboard?duplicate=1")
            return self.redirect("/dashboard?success=1")

        if path == "/logout":
            sid = self.cookies.get("sid")
            if sid:
                with SESSION_LOCK:
                    SESSIONS.pop(sid, None)
            return self.redirect("/", [("Set-Cookie", "sid=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0")])

        return self.send_html(page("Not Found", "<section class='card'><h1>Page not found</h1></section>"), 404)

def main():
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), App)
    print("=" * 62)
    print("Online Course Registration System is running!")
    print(f"Open in your browser: http://{HOST}:{PORT}")
    print(f"Database file: {DB_FILE}")
    print("Stop the server by pressing Ctrl+C in this terminal.")
    print("=" * 62)
    try:
        threading.Timer(1.0, lambda: webbrowser.open(f"http://{HOST}:{PORT}")).start()
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
