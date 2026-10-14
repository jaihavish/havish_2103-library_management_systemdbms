"""Runs the report's test cases on a fresh database and prints the real outcomes."""
import os, sys, json
sys.path.insert(0, r"D:\denos\hp1\app")
sys.path.insert(0, r"D:\denos\hp1\tests")
os.environ["LIB_DB_PASSWORD"] = "12345678"
import mysql.connector
import library
from library import Library, LibraryError
from test_library import run_script

admin = mysql.connector.connect(host="localhost", user="root", password="12345678")
for f in ("01_schema.sql", "02_sample_data.sql", "03_views.sql"):
    run_script(admin, f)
admin.close()
lib = Library(library.connect())
out = {}


def attempt(tc, fn):
    try:
        r = fn()
        out[tc] = "OK: " + str(r)
    except LibraryError as e:
        out[tc] = "REFUSED: " + str(e)
    except mysql.connector.Error as e:
        out[tc] = "DBERROR: " + str(e)
    print(tc, "->", out[tc])


attempt("TC01", lambda: lib.issue_book("LIB2025007", "ACC-0002"))
attempt("TC02a", lambda: lib.issue_book("LIB2025007", "ACC-0003"))
attempt("TC02b", lambda: lib.issue_book("LIB2025007", "ACC-0004"))
attempt("TC02", lambda: lib.issue_book("LIB2025007", "ACC-0005"))
attempt("TC03", lambda: lib.issue_book("LIB2025002", "ACC-0001"))
attempt("TC04", lambda: lib.issue_book("LIB2023015", "ACC-0007"))
attempt("TC05", lambda: lib.return_book("ACC-0001"))
attempt("TC06", lambda: lib.return_book("ACC-0002"))
attempt("TC07", lambda: lib.return_book("ACC-0008"))
attempt("TC08", lambda: lib.reserve("LIB2025001", "9780078022159"))
attempt("TC09a", lambda: lib.issue_book("LIB2025006", "ACC-0015"))
attempt("TC09b", lambda: lib.reserve("LIB2025001", "9780132350884"))
attempt("TC09c", lambda: lib.return_book("ACC-0013"))
print(lib.rows("SELECT status, copy_id FROM reservation WHERE edition_id=6"))
print(lib.rows("SELECT status FROM copy WHERE accession_no='ACC-0013'"))
attempt("TC10", lambda: lib.issue_book("LIB2025005", "ACC-0029"))
attempt("TC11", lambda: lib.add_book("Another", 1, "A", "P", "9780078022159", 1, 2020, 100))
attempt("TC12", lambda: lib.add_book("Short", 1, "A", "P", "12345", 1, 2020, 100))
attempt("TC13", lambda: lib.register_member("LIB900", "T", "not-an-email", "", "STUDENT"))
fid = lib.rows("SELECT fine_id FROM fine WHERE issue_id=12")[0]["fine_id"]
attempt("TC14a", lambda: lib.pay_fine(fid, "100"))
attempt("TC14", lambda: lib.pay_fine(fid, "10"))
attempt("TC15", lambda: lib.log_digital_access("LIB2025001", 6, 30))
c = lib.conn.cursor()
try:
    c.execute("INSERT INTO issue (copy_id, member_id, issue_date, due_date) VALUES (10, 7, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 7 DAY))")
except mysql.connector.Error as e:
    out["TC16"] = f"DBERROR {e.errno}: {e.msg}"
lib.conn.rollback()
try:
    c.execute("INSERT INTO fine (issue_id, days_late, amount) VALUES (1, 1, -5)")
except mysql.connector.Error as e:
    out["TC17"] = f"DBERROR {e.errno}: {e.msg}"
lib.conn.rollback()
print(out["TC16"]); print(out["TC17"])
print(lib.rows("SELECT VERSION() v"))
rows = lib.rows("SELECT table_name t, table_rows r FROM information_schema.tables WHERE table_schema='library_db' ORDER BY table_name")
print(rows)
for t in [r["t"] for r in rows]:
    pass
json.dump(out, open(r"D:\denos\hp1\tmp\scen.json", "w"), indent=1)
