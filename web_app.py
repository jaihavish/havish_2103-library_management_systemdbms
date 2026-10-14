import os
import sys
import re
import csv
import io
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from flask import Flask, render_template, request, jsonify, Response, send_file

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))
import library
from library import Library, LibraryError, dashboard_stats, member_choices, available_copies
from library import loans_out, reservable_editions, all_members, all_fines, catalogue, REPORTS, member_history

app = Flask(__name__, template_folder="templates", static_folder="static")

# Custom JSON encoder helper
def clean_val(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="ignore")
    return v

def clean_data(obj):
    if isinstance(obj, list):
        return [clean_data(item) for item in obj]
    if isinstance(obj, dict):
        return {k: clean_data(v) for k, v in obj.items()}
    return clean_val(obj)

# Global database connection state
db_state = {
    "connected": False,
    "mode": "disconnected", # "mysql", "demo", "disconnected"
    "error": None,
    "host": os.environ.get("LIB_DB_HOST", "localhost"),
    "port": int(os.environ.get("LIB_DB_PORT", "3306")),
    "user": os.environ.get("LIB_DB_USER", "root"),
    "database": os.environ.get("LIB_DB_NAME", "library_db"),
}

current_lib = None
current_conn = None

def run_sql_file(conn, filename):
    sql_path = os.path.join(os.path.dirname(__file__), "sql", filename)
    if not os.path.exists(sql_path):
        return
    with open(sql_path, "r", encoding="utf-8") as f:
        text = f.read()
    text = re.sub(r"--[^\n]*", "", text)
    cur = conn.cursor()
    for stmt in text.split(";"):
        stmt = stmt.strip()
        if stmt:
            cur.execute(stmt)
    conn.commit()
    cur.close()

def try_connect_mysql(password=None, auto_init=True):
    global current_lib, current_conn, db_state
    import mysql.connector
    
    pwd = password if password is not None else os.environ.get("LIB_DB_PASSWORD", "")
    host = db_state["host"]
    port = db_state["port"]
    user = db_state["user"]
    db_name = db_state["database"]
    
    # First try connecting directly to the database
    try:
        conn = mysql.connector.connect(
            host=host, port=port, user=user, password=pwd, database=db_name, autocommit=False
        )
        current_conn = conn
        current_lib = Library(conn)
        db_state["connected"] = True
        db_state["mode"] = "mysql"
        db_state["error"] = None
        return True, "Connected to MySQL successfully."
    except mysql.connector.Error as err:
        # If database doesn't exist (1049), connect to server and create it
        if err.errno == 1049 or auto_init:
            try:
                admin_conn = mysql.connector.connect(
                    host=host, port=port, user=user, password=pwd, autocommit=True
                )
                if auto_init:
                    for f in ("01_schema.sql", "02_sample_data.sql", "03_views.sql"):
                        run_sql_file(admin_conn, f)
                admin_conn.close()
                
                # Now reconnect to library_db
                conn = mysql.connector.connect(
                    host=host, port=port, user=user, password=pwd, database=db_name, autocommit=False
                )
                current_conn = conn
                current_lib = Library(conn)
                db_state["connected"] = True
                db_state["mode"] = "mysql"
                db_state["error"] = None
                return True, "Database initialized and connected successfully."
            except Exception as e2:
                db_state["connected"] = False
                db_state["error"] = str(e2)
                return False, str(e2)
        else:
            db_state["connected"] = False
            db_state["error"] = str(err)
            return False, str(err)

# In-Memory Demo Mock Store for Instant Zero-Setup Preview
class DemoLibrary:
    def __init__(self):
        self.categories_list = [
            {"category_id": 1, "name": "Computer Science"},
            {"category_id": 2, "name": "Mathematics"},
            {"category_id": 3, "name": "Physics"},
            {"category_id": 4, "name": "Literature"},
            {"category_id": 5, "name": "General Science"}
        ]
        self.books = [
            {"book_id": 1, "title": "Database System Concepts", "category_id": 1, "category": "Computer Science",
             "authors": "Avi Silberschatz, Henry F. Korth, S. Sudarshan", "isbn": "9780078022159", "edition_no": 7,
             "pub_year": 2019, "pages": 1376, "publisher": "McGraw-Hill",
             "copies": [
                 {"copy_id": 1, "accession_no": "ACC-CS-001", "shelf": "CS-A1-01", "status": "AVAILABLE"},
                 {"copy_id": 2, "accession_no": "ACC-CS-002", "shelf": "CS-A1-02", "status": "ISSUED"},
                 {"copy_id": 3, "accession_no": "ACC-CS-003", "shelf": "CS-A1-03", "status": "AVAILABLE"}
             ]},
            {"book_id": 2, "title": "Introduction to Algorithms", "category_id": 1, "category": "Computer Science",
             "authors": "Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, Clifford Stein", "isbn": "9780262033848", "edition_no": 3,
             "pub_year": 2009, "pages": 1292, "publisher": "MIT Press",
             "copies": [
                 {"copy_id": 4, "accession_no": "ACC-CS-004", "shelf": "CS-B2-01", "status": "ISSUED"},
                 {"copy_id": 5, "accession_no": "ACC-CS-005", "shelf": "CS-B2-02", "status": "AVAILABLE"}
             ]},
            {"book_id": 3, "title": "Operating System Concepts", "category_id": 1, "category": "Computer Science",
             "authors": "Abraham Silberschatz, Peter B. Galvin, Greg Gagne", "isbn": "9781119800361", "edition_no": 10,
             "pub_year": 2018, "pages": 1200, "publisher": "Wiley",
             "copies": [
                 {"copy_id": 6, "accession_no": "ACC-CS-006", "shelf": "CS-C1-01", "status": "AVAILABLE"},
                 {"copy_id": 7, "accession_no": "ACC-CS-007", "shelf": "CS-C1-02", "status": "ON_HOLD"}
             ]},
            {"book_id": 4, "title": "Clean Code: A Handbook of Agile Software Craftsmanship", "category_id": 1, "category": "Computer Science",
             "authors": "Robert C. Martin", "isbn": "9780132350884", "edition_no": 1,
             "pub_year": 2008, "pages": 464, "publisher": "Prentice Hall",
             "copies": [
                 {"copy_id": 8, "accession_no": "ACC-CS-008", "shelf": "CS-D3-01", "status": "AVAILABLE"}
             ]},
            {"book_id": 5, "title": "Discrete Mathematics and Its Applications", "category_id": 2, "category": "Mathematics",
             "authors": "Kenneth H. Rosen", "isbn": "9781259676512", "edition_no": 8,
             "pub_year": 2019, "pages": 1024, "publisher": "McGraw-Hill",
             "copies": [
                 {"copy_id": 9, "accession_no": "ACC-MA-001", "shelf": "MA-A1-01", "status": "AVAILABLE"},
                 {"copy_id": 10, "accession_no": "ACC-MA-002", "shelf": "MA-A1-02", "status": "AVAILABLE"}
             ]}
        ]
        self.members = [
            {"card_no": "LIB2025001", "full_name": "Aarav Sharma", "email": "aarav.sharma@example.edu", "phone": "9876543210",
             "member_type": "STUDENT", "expiry_date": (date.today() + timedelta(days=365)).isoformat(), "status": "ACTIVE", "max_books": 3, "loan_days": 14, "fine_per_day": 2.0},
            {"card_no": "LIB2025002", "full_name": "Dr. Priya Patel", "email": "priya.patel@example.edu", "phone": "9876543211",
             "member_type": "FACULTY", "expiry_date": (date.today() + timedelta(days=730)).isoformat(), "status": "ACTIVE", "max_books": 6, "loan_days": 30, "fine_per_day": 1.0},
            {"card_no": "LIB2025003", "full_name": "Rohan Verma", "email": "rohan.verma@example.com", "phone": "9876543212",
             "member_type": "PUBLIC", "expiry_date": (date.today() + timedelta(days=180)).isoformat(), "status": "ACTIVE", "max_books": 2, "loan_days": 7, "fine_per_day": 5.0},
            {"card_no": "LIB2025004", "full_name": "Ananya Sen", "email": "ananya.sen@example.edu", "phone": "9876543213",
             "member_type": "STUDENT", "expiry_date": (date.today() + timedelta(days=300)).isoformat(), "status": "ACTIVE", "max_books": 3, "loan_days": 14, "fine_per_day": 2.0}
        ]
        self.issues = [
            {"issue_id": 1, "accession_no": "ACC-CS-002", "title": "Database System Concepts", "member": "Aarav Sharma",
             "card_no": "LIB2025001", "issue_date": (date.today() - timedelta(days=20)).isoformat(),
             "due_date": (date.today() - timedelta(days=6)).isoformat(), "return_date": None, "days_late": 6},
            {"issue_id": 2, "accession_no": "ACC-CS-004", "title": "Introduction to Algorithms", "member": "Dr. Priya Patel",
             "card_no": "LIB2025002", "issue_date": (date.today() - timedelta(days=10)).isoformat(),
             "due_date": (date.today() + timedelta(days=20)).isoformat(), "return_date": None, "days_late": 0}
        ]
        self.fines = [
            {"fine_id": 1, "member": "Aarav Sharma", "card_no": "LIB2025001", "title": "Database System Concepts",
             "days_late": 6, "amount": 12.0, "paid_amount": 0.0, "balance": 12.0}
        ]
        self.reservations_list = [
            {"reservation_id": 1, "title": "Operating System Concepts", "position_in_line": 1,
             "full_name": "Ananya Sen", "status": "READY", "reserved_on": (date.today() - timedelta(days=3)).isoformat()}
        ]
        self.digital = [
            {"resource_id": 1, "title": "ACM Digital Library", "resource_type": "JOURNAL", "url": "https://dl.acm.org", "licence_end": "2027-12-31"},
            {"resource_id": 2, "title": "O'Reilly Learning Platform", "resource_type": "EBOOK", "url": "https://learning.oreilly.com", "licence_end": "2027-06-30"},
            {"resource_id": 3, "title": "MIT OpenCourseWare Algorithms", "resource_type": "VIDEO", "url": "https://ocw.mit.edu", "licence_end": None}
        ]
        self.digital_logs = [
            {"log_id": 1, "resource_id": 1, "card_no": "LIB2025001", "minutes": 45, "date": date.today().isoformat()}
        ]

    def stats(self):
        available = sum(1 for b in self.books for c in b["copies"] if c["status"] == "AVAILABLE")
        loans = len([i for i in self.issues if i["return_date"] is None])
        overdue = len([i for i in self.issues if i["return_date"] is None and i["days_late"] > 0])
        unpaid = sum(f["balance"] for f in self.fines)
        return {
            "Titles": len(self.books),
            "Copies on shelf": available,
            "Books on loan": loans,
            "Overdue": overdue,
            "Active members": len(self.members),
            "Waiting reservations": len(self.reservations_list),
            "Unpaid fines (Rs)": unpaid,
            "Digital visits": len(self.digital_logs)
        }

demo_lib = DemoLibrary()

# Startup attempt: try connecting with default settings if possible
try:
    try_connect_mysql(auto_init=False)
except Exception:
    pass

if not db_state["connected"]:
    db_state["mode"] = "demo"

# ---------------- API ROUTES ----------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def api_status():
    return jsonify({
        "connected": db_state["connected"],
        "mode": db_state["mode"],
        "error": db_state["error"],
        "host": db_state["host"],
        "port": db_state["port"],
        "user": db_state["user"],
        "database": db_state["database"]
    })

@app.route("/api/connect", methods=["POST"])
def api_connect():
    data = request.json or {}
    password = data.get("password", "")
    if "host" in data: db_state["host"] = data["host"]
    if "port" in data: db_state["port"] = int(data["port"])
    if "user" in data: db_state["user"] = data["user"]
    if "database" in data: db_state["database"] = data["database"]
    auto_init = data.get("init_sample_data", True)

    success, msg = try_connect_mysql(password, auto_init=auto_init)
    if success:
        return jsonify({"success": True, "message": msg, "mode": "mysql"})
    else:
        return jsonify({"success": False, "error": msg, "mode": db_state["mode"]}), 400

@app.route("/api/reseed", methods=["POST"])
def api_reseed():
    if db_state["mode"] != "mysql" or not current_conn:
        return jsonify({"success": False, "error": "Not connected to MySQL."}), 400
    try:
        for f in ("01_schema.sql", "02_sample_data.sql", "03_views.sql"):
            run_sql_file(current_conn, f)
        return jsonify({"success": True, "message": "Database successfully re-seeded with schema, data, and views."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/dashboard")
def api_dashboard():
    if db_state["mode"] == "mysql" and current_lib:
        try:
            stats = dashboard_stats(current_lib)
            recent_loans = loans_out(current_lib)[:5]
            overdue = current_lib.rows("SELECT accession_no, title, full_name, due_date, days_overdue, fine_so_far FROM v_overdue_copies ORDER BY days_overdue DESC LIMIT 5")
            return jsonify(clean_data({
                "stats": stats,
                "recent_loans": recent_loans,
                "overdue": overdue
            }))
        except Exception as e:
            pass
    # Fallback demo
    return jsonify({
        "stats": demo_lib.stats(),
        "recent_loans": demo_lib.issues[:5],
        "overdue": [i for i in demo_lib.issues if i["days_late"] > 0]
    })

@app.route("/api/catalogue", methods=["GET"])
def api_catalogue():
    q = request.args.get("q", "").strip()
    if db_state["mode"] == "mysql" and current_lib:
        try:
            if q:
                books = current_lib.search(q)
            else:
                books = catalogue(current_lib)
            categories = current_lib.categories()
            return jsonify(clean_data({"books": books, "categories": categories}))
        except Exception as e:
            pass

    # Fallback demo
    filtered = demo_lib.books
    if q:
        filtered = [b for b in demo_lib.books if q.lower() in b["title"].lower() or q.lower() in b["authors"].lower() or q.lower() in b["category"].lower() or q in b["isbn"]]
    res_books = []
    for b in filtered:
        avail = sum(1 for c in b["copies"] if c["status"] == "AVAILABLE")
        total = sum(1 for c in b["copies"] if c["status"] != "WITHDRAWN")
        res_books.append({
            "title": b["title"], "authors": b["authors"], "isbn": b["isbn"],
            "edition_no": b["edition_no"], "category": b["category"],
            "available": avail, "copies": total,
            "copy_list": b["copies"]
        })
    return jsonify({"books": res_books, "categories": demo_lib.categories_list})

@app.route("/api/catalogue/book", methods=["POST"])
def api_add_book():
    data = request.json or {}
    title = data.get("title")
    category_id = data.get("category_id")
    authors = data.get("authors")
    publisher = data.get("publisher")
    isbn = data.get("isbn")
    edition_no = data.get("edition_no", 1)
    pub_year = data.get("pub_year")
    pages = data.get("pages")

    if db_state["mode"] == "mysql" and current_lib:
        try:
            current_lib.add_book(title, category_id, authors, publisher, isbn, edition_no, pub_year, pages)
            return jsonify({"success": True, "message": "Book added successfully."})
        except LibraryError as le:
            return jsonify({"success": False, "error": str(le)}), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # Demo mode add
    cat_name = next((c["name"] for c in demo_lib.categories_list if c["category_id"] == int(category_id)), "General")
    demo_lib.books.append({
        "book_id": len(demo_lib.books) + 1, "title": title, "category_id": int(category_id), "category": cat_name,
        "authors": authors, "isbn": isbn, "edition_no": int(edition_no), "pub_year": pub_year, "pages": pages,
        "publisher": publisher, "copies": []
    })
    return jsonify({"success": True, "message": "Book added to demo catalogue."})

@app.route("/api/catalogue/copy", methods=["POST"])
def api_add_copy():
    data = request.json or {}
    isbn = data.get("isbn")
    accession_no = data.get("accession_no")
    shelf = data.get("shelf", "")

    if db_state["mode"] == "mysql" and current_lib:
        try:
            current_lib.add_copy(isbn, accession_no, shelf)
            return jsonify({"success": True, "message": "Copy added successfully."})
        except LibraryError as le:
            return jsonify({"success": False, "error": str(le)}), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    for b in demo_lib.books:
        if b["isbn"] == isbn:
            b["copies"].append({"copy_id": len(b["copies"])+1, "accession_no": accession_no, "shelf": shelf, "status": "AVAILABLE"})
            return jsonify({"success": True, "message": "Copy added to demo catalogue."})
    return jsonify({"success": False, "error": "Book not found."}), 404

@app.route("/api/members", methods=["GET"])
def api_members():
    q = request.args.get("q", "").strip()
    if db_state["mode"] == "mysql" and current_lib:
        try:
            members = current_lib.find_members(q) if q else all_members(current_lib)
            return jsonify(clean_data(members))
        except Exception:
            pass

    members = demo_lib.members
    if q:
        members = [m for m in members if q.lower() in m["full_name"].lower() or q.lower() in m["card_no"].lower() or q.lower() in m["email"].lower()]
    return jsonify(members)

@app.route("/api/members", methods=["POST"])
def api_register_member():
    data = request.json or {}
    card_no = data.get("card_no")
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    member_type = data.get("member_type", "STUDENT")
    years = data.get("years", 1)

    if db_state["mode"] == "mysql" and current_lib:
        try:
            current_lib.register_member(card_no, name, email, phone, member_type, years)
            return jsonify({"success": True, "message": "Member registered successfully."})
        except LibraryError as le:
            return jsonify({"success": False, "error": str(le)}), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    demo_lib.members.append({
        "card_no": card_no, "full_name": name, "email": email, "phone": phone,
        "member_type": member_type, "expiry_date": (date.today() + timedelta(days=365*int(years))).isoformat(),
        "status": "ACTIVE"
    })
    return jsonify({"success": True, "message": "Member registered in demo mode."})

@app.route("/api/members/<card_no>/history")
def api_member_history(card_no):
    if db_state["mode"] == "mysql" and current_lib:
        try:
            hist = member_history(current_lib, card_no)
            return jsonify(clean_data(hist))
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    hist = [i for i in demo_lib.issues if i.get("card_no") == card_no]
    return jsonify(hist)

@app.route("/api/circulation/choices")
def api_circulation_choices():
    if db_state["mode"] == "mysql" and current_lib:
        try:
            members = member_choices(current_lib)
            copies = available_copies(current_lib)
            loans = loans_out(current_lib)
            return jsonify(clean_data({"members": members, "copies": copies, "loans": loans}))
        except Exception:
            pass

    members = [{"card_no": m["card_no"], "full_name": m["full_name"], "member_type": m["member_type"]} for m in demo_lib.members if m["status"] == "ACTIVE"]
    avail_copies = [{"accession_no": c["accession_no"], "title": b["title"]} for b in demo_lib.books for c in b["copies"] if c["status"] in ("AVAILABLE", "ON_HOLD")]
    return jsonify({"members": members, "copies": avail_copies, "loans": demo_lib.issues})

@app.route("/api/circulation/issue", methods=["POST"])
def api_issue():
    data = request.json or {}
    card_no = data.get("card_no")
    accession_no = data.get("accession_no")
    staff_id = data.get("staff_id", 1)

    if db_state["mode"] == "mysql" and current_lib:
        try:
            due = current_lib.issue_book(card_no, accession_no, staff_id)
            return jsonify({"success": True, "message": f"Issued successfully! Due date: {due.isoformat()}", "due_date": due.isoformat()})
        except LibraryError as le:
            return jsonify({"success": False, "error": str(le)}), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # Demo mode issue
    target_book = None
    target_copy = None
    for b in demo_lib.books:
        for c in b["copies"]:
            if c["accession_no"] == accession_no:
                target_book = b
                target_copy = c
                break
    m = next((m for m in demo_lib.members if m["card_no"] == card_no), None)
    if not m: return jsonify({"success": False, "error": "Member not found."}), 404
    if not target_copy or target_copy["status"] != "AVAILABLE":
        return jsonify({"success": False, "error": "Copy not available."}), 400

    target_copy["status"] = "ISSUED"
    due = (date.today() + timedelta(days=m.get("loan_days", 14))).isoformat()
    demo_lib.issues.append({
        "issue_id": len(demo_lib.issues) + 1, "accession_no": accession_no, "title": target_book["title"],
        "member": m["full_name"], "card_no": card_no, "issue_date": date.today().isoformat(),
        "due_date": due, "return_date": None, "days_late": 0
    })
    return jsonify({"success": True, "message": f"Book issued! Due date: {due}"})

@app.route("/api/circulation/return", methods=["POST"])
def api_return():
    data = request.json or {}
    accession_no = data.get("accession_no")

    if db_state["mode"] == "mysql" and current_lib:
        try:
            fine = current_lib.return_book(accession_no)
            msg = f"Book returned! Late fine: Rs {fine:.2f}" if fine > 0 else "Book returned on time with no fine."
            return jsonify({"success": True, "message": msg, "fine": float(fine)})
        except LibraryError as le:
            return jsonify({"success": False, "error": str(le)}), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # Demo mode return
    issue = next((i for i in demo_lib.issues if i["accession_no"] == accession_no and i["return_date"] is None), None)
    if not issue: return jsonify({"success": False, "error": "That copy is not out on loan."}), 400

    issue["return_date"] = date.today().isoformat()
    for b in demo_lib.books:
        for c in b["copies"]:
            if c["accession_no"] == accession_no:
                c["status"] = "AVAILABLE"

    fine = issue["days_late"] * 2.0
    if fine > 0:
        demo_lib.fines.append({
            "fine_id": len(demo_lib.fines)+1, "member": issue["member"], "card_no": issue["card_no"],
            "title": issue["title"], "days_late": issue["days_late"], "amount": fine, "paid_amount": 0.0, "balance": fine
        })
    return jsonify({"success": True, "message": f"Returned. Late fine: Rs {fine}", "fine": fine})

@app.route("/api/circulation/renew", methods=["POST"])
def api_renew():
    data = request.json or {}
    accession_no = data.get("accession_no")

    if db_state["mode"] == "mysql" and current_lib:
        try:
            new_due = current_lib.renew_book(accession_no)
            return jsonify({"success": True, "message": f"Renewed! New due date: {new_due.isoformat()}"})
        except LibraryError as le:
            return jsonify({"success": False, "error": str(le)}), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    issue = next((i for i in demo_lib.issues if i["accession_no"] == accession_no and i["return_date"] is None), None)
    if not issue: return jsonify({"success": False, "error": "Not currently issued."}), 400
    new_due = (date.today() + timedelta(days=14)).isoformat()
    issue["due_date"] = new_due
    return jsonify({"success": True, "message": f"Renewed! New due date: {new_due}"})

@app.route("/api/reservations", methods=["GET"])
def api_reservations():
    if db_state["mode"] == "mysql" and current_lib:
        try:
            res = current_lib.reservations()
            reservable = reservable_editions(current_lib)
            return jsonify(clean_data({"reservations": res, "reservable": reservable}))
        except Exception:
            pass
    return jsonify({"reservations": demo_lib.reservations_list, "reservable": [{"isbn": "9781119800361", "title": "Operating System Concepts", "edition_no": 10}]})

@app.route("/api/reservations", methods=["POST"])
def api_add_reservation():
    data = request.json or {}
    card_no = data.get("card_no")
    isbn = data.get("isbn")

    if db_state["mode"] == "mysql" and current_lib:
        try:
            q_no = current_lib.reserve(card_no, isbn)
            return jsonify({"success": True, "message": f"Reservation placed! Queue position: #{q_no}"})
        except LibraryError as le:
            return jsonify({"success": False, "error": str(le)}), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    m = next((m for m in demo_lib.members if m["card_no"] == card_no), None)
    demo_lib.reservations_list.append({
        "reservation_id": len(demo_lib.reservations_list)+1, "title": "Reserved Book", "position_in_line": len(demo_lib.reservations_list)+1,
        "full_name": m["full_name"] if m else card_no, "status": "WAITING", "reserved_on": date.today().isoformat()
    })
    return jsonify({"success": True, "message": f"Reservation placed! Queue position: #{len(demo_lib.reservations_list)}"})

@app.route("/api/reservations/<int:res_id>", methods=["DELETE"])
def api_cancel_reservation(res_id):
    if db_state["mode"] == "mysql" and current_lib:
        try:
            current_lib.cancel_reservation(res_id)
            return jsonify({"success": True, "message": "Reservation cancelled."})
        except LibraryError as le:
            return jsonify({"success": False, "error": str(le)}), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    demo_lib.reservations_list = [r for r in demo_lib.reservations_list if r["reservation_id"] != res_id]
    return jsonify({"success": True, "message": "Reservation cancelled."})

@app.route("/api/fines", methods=["GET"])
def api_fines():
    unpaid = request.args.get("unpaid_only", "0") == "1"
    if db_state["mode"] == "mysql" and current_lib:
        try:
            fines = all_fines(current_lib, unpaid_only=unpaid)
            return jsonify(clean_data(fines))
        except Exception:
            pass

    fines = demo_lib.fines
    if unpaid:
        fines = [f for f in fines if f["balance"] > 0]
    return jsonify(fines)

@app.route("/api/fines/pay", methods=["POST"])
def api_pay_fine():
    data = request.json or {}
    fine_id = data.get("fine_id")
    amount = data.get("amount")

    if db_state["mode"] == "mysql" and current_lib:
        try:
            bal = current_lib.pay_fine(fine_id, amount)
            return jsonify({"success": True, "message": f"Payment recorded! Remaining balance: Rs {bal:.2f}", "remaining": float(bal)})
        except LibraryError as le:
            return jsonify({"success": False, "error": str(le)}), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    f = next((f for f in demo_lib.fines if f["fine_id"] == int(fine_id)), None)
    if not f: return jsonify({"success": False, "error": "Fine not found."}), 404
    amt = float(amount)
    if amt > f["balance"]: return jsonify({"success": False, "error": f"Amount exceeds balance Rs {f['balance']}"}), 400
    f["paid_amount"] += amt
    f["balance"] -= amt
    return jsonify({"success": True, "message": f"Payment recorded! Remaining balance: Rs {f['balance']:.2f}", "remaining": f["balance"]})

@app.route("/api/digital", methods=["GET"])
def api_digital():
    if db_state["mode"] == "mysql" and current_lib:
        try:
            res = current_lib.digital_resources()
            return jsonify(clean_data(res))
        except Exception:
            pass
    return jsonify(demo_lib.digital)

@app.route("/api/digital/access", methods=["POST"])
def api_digital_access():
    data = request.json or {}
    card_no = data.get("card_no")
    resource_id = data.get("resource_id")
    minutes = data.get("minutes", 30)

    if db_state["mode"] == "mysql" and current_lib:
        try:
            current_lib.log_digital_access(card_no, resource_id, minutes)
            return jsonify({"success": True, "message": "Access session logged successfully."})
        except LibraryError as le:
            return jsonify({"success": False, "error": str(le)}), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    demo_lib.digital_logs.append({
        "log_id": len(demo_lib.digital_logs)+1, "resource_id": resource_id, "card_no": card_no,
        "minutes": minutes, "date": date.today().isoformat()
    })
    return jsonify({"success": True, "message": "Access session logged in demo mode."})

@app.route("/api/reports/<report_key>")
def api_reports(report_key):
    as_csv = request.args.get("csv", "0") == "1"
    name_map = {
        "overdue": "Overdue copies",
        "popular": "Popular books",
        "reservations": "Reservation queue",
        "fines": "Fine collection by month",
        "active_loans": "Books currently on loan",
        "digital": "Digital resource usage",
        "available": "Available titles"
    }
    sql_name = name_map.get(report_key, "Overdue copies")
    
    rows = []
    if db_state["mode"] == "mysql" and current_lib and sql_name in REPORTS:
        try:
            rows = current_lib.rows(REPORTS[sql_name])
            rows = clean_data(rows)
        except Exception as e:
            rows = []
    
    if not rows:
        # Demo data for reports
        if report_key == "popular":
            rows = [
                {"title": "Database System Concepts", "times_issued": 18},
                {"title": "Introduction to Algorithms", "times_issued": 14},
                {"title": "Operating System Concepts", "times_issued": 11},
                {"title": "Clean Code", "times_issued": 9},
                {"title": "Discrete Mathematics", "times_issued": 5}
            ]
        elif report_key == "fines":
            rows = [
                {"month": "2026-08", "fines_raised": 4, "total_fined": 68.0, "total_collected": 50.0, "still_pending": 18.0},
                {"month": "2026-09", "fines_raised": 6, "total_fined": 110.0, "total_collected": 85.0, "still_pending": 25.0},
                {"month": "2026-10", "fines_raised": 3, "total_fined": 36.0, "total_collected": 24.0, "still_pending": 12.0}
            ]
        elif report_key == "overdue":
            rows = [
                {"accession_no": "ACC-CS-002", "title": "Database System Concepts", "full_name": "Aarav Sharma", "due_date": (date.today() - timedelta(days=6)).isoformat(), "days_overdue": 6, "fine_so_far": 12.0}
            ]
        else:
            rows = [{"info": "No report data available for this query."}]

    if as_csv and rows:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=report_{report_key}.csv"}
        )

    return jsonify({"report": sql_name, "data": rows})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n=======================================================")
    print(f" Library Management System Web Interface")
    print(f" Local URL: http://localhost:{port}")
    print(f" Database Mode: {db_state['mode']}")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=False)
