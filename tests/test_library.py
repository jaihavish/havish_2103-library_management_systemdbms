"""Tests for the library database and the rules in app/library.py.

Needs a MySQL server. Use LIB_DB_HOST / LIB_DB_PORT / LIB_DB_USER / LIB_DB_PASSWORD.
The test run DROPS and rebuilds the database called library_db, so do not point
it at a server that holds data you want to keep.

Run from the project folder:   python -m unittest discover -s tests -v
"""
import os
import re
import sys
import unittest
from datetime import date, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
import library                                    # noqa: E402
from library import Library, LibraryError         # noqa: E402
import mysql.connector                            # noqa: E402

SQL_DIR = os.path.join(os.path.dirname(__file__), "..", "sql")
TODAY = date.today()


def run_script(conn, name):
    with open(os.path.join(SQL_DIR, name), encoding="utf8") as fh:
        text = fh.read()
    text = re.sub(r"--[^\n]*", "", text)
    cur = conn.cursor()
    for stmt in text.split(";"):
        if stmt.strip():
            cur.execute(stmt)
    conn.commit()
    cur.close()


class Base(unittest.TestCase):
    def setUp(self):
        admin = mysql.connector.connect(
            host=os.environ.get("LIB_DB_HOST", "localhost"),
            port=int(os.environ.get("LIB_DB_PORT", "3306")),
            user=os.environ.get("LIB_DB_USER", "root"),
            password=os.environ.get("LIB_DB_PASSWORD", ""))
        for f in ("01_schema.sql", "02_sample_data.sql", "03_views.sql"):
            run_script(admin, f)
        admin.close()
        conn = library.connect()
        self.lib = Library(conn)
        self.conn = conn

    def tearDown(self):
        self.conn.close()

    def one(self, sql, params=()):
        return self.lib.rows(sql, params)[0]

    def status(self, acc):
        return self.one("SELECT status FROM copy WHERE accession_no=%s", (acc,))["status"]


class InputChecks(Base):
    def test_bad_isbn(self):
        with self.assertRaises(LibraryError):
            self.lib.add_book("X", 1, "A", "P", "12345", 1, 2020, 100)

    def test_empty_title(self):
        with self.assertRaises(LibraryError):
            self.lib.add_book("  ", 1, "A", "P", "9781234567897", 1, 2020, 100)

    def test_bad_email_and_phone(self):
        with self.assertRaises(LibraryError):
            self.lib.register_member("LIB900", "Test", "not-an-email", "", "STUDENT")
        with self.assertRaises(LibraryError):
            self.lib.register_member("LIB900", "Test", "t@x.com", "12ab", "STUDENT")

    def test_future_year_rejected(self):
        with self.assertRaises(LibraryError):
            self.lib.add_book("X", 1, "A", "P", "9781234567897", 1, 3000, 100)


class Catalogue(Base):
    def test_add_book_and_copy_then_search(self):
        self.lib.add_book("Test Driven Design", 1, "Jane Roe, John Doe", "New Press",
                          "9781234567897", 1, 2021, 300)
        self.lib.add_copy("9781234567897", "ACC-9001", "CS-Z1")
        found = self.lib.search("Test Driven")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["available"], 1)
        self.assertIn("Jane Roe", found[0]["authors"])

    def test_duplicate_isbn_refused(self):
        with self.assertRaises(LibraryError):
            self.lib.add_book("Another", 1, "A", "P", "9780078022159", 1, 2020, 100)

    def test_duplicate_accession_refused(self):
        with self.assertRaises(LibraryError):
            self.lib.add_copy("9780078022159", "ACC-0001")

    def test_search_by_author(self):
        titles = {r["title"] for r in self.lib.search("Silberschatz")}
        self.assertIn("Database System Concepts", titles)

    def test_cannot_withdraw_issued_copy(self):
        with self.assertRaises(LibraryError):
            self.lib.remove_copy("ACC-0001")
        self.lib.remove_copy("ACC-0002")
        self.assertEqual(self.status("ACC-0002"), "WITHDRAWN")


class Issuing(Base):
    def test_issue_sets_due_date_and_status(self):
        due = self.lib.issue_book("LIB2025007", "ACC-0002")
        self.assertEqual(due, TODAY + timedelta(days=14))
        self.assertEqual(self.status("ACC-0002"), "ISSUED")

    def test_faculty_gets_longer_loan(self):
        due = self.lib.issue_book("LIB2024101", "ACC-0003")
        self.assertEqual(due, TODAY + timedelta(days=30))

    def test_issued_copy_cannot_be_issued_again(self):
        with self.assertRaises(LibraryError):
            self.lib.issue_book("LIB2025007", "ACC-0001")

    def test_database_blocks_two_active_issues_on_one_copy(self):
        cur = self.conn.cursor()
        with self.assertRaises(mysql.connector.Error):
            cur.execute("INSERT INTO issue (copy_id, member_id, issue_date, due_date) "
                        "VALUES (1, 7, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 7 DAY))")
        self.conn.rollback()

    def test_student_limit_is_three(self):
        for acc in ("ACC-0002", "ACC-0003", "ACC-0004"):
            self.lib.issue_book("LIB2025007", acc)
        with self.assertRaises(LibraryError) as e:
            self.lib.issue_book("LIB2025007", "ACC-0005")
        self.assertIn("Limit", str(e.exception))
        self.assertEqual(self.status("ACC-0005"), "AVAILABLE")   # nothing half-done

    def test_expired_member_blocked(self):
        with self.assertRaises(LibraryError):
            self.lib.issue_book("LIB2023015", "ACC-0002")

    def test_unknown_member_and_copy(self):
        with self.assertRaises(LibraryError):
            self.lib.issue_book("NOPE", "ACC-0002")
        with self.assertRaises(LibraryError):
            self.lib.issue_book("LIB2025007", "ACC-9999")

    def test_member_with_big_fine_blocked(self):
        # Karan (LIB2025005) owes Rs 12 in the sample data, so he can borrow
        self.lib.issue_book("LIB2025005", "ACC-0002")
        # raise his unpaid fine above the Rs 50 limit
        self.conn.cursor().execute("UPDATE fine SET amount=60 WHERE issue_id=18")
        self.conn.commit()
        with self.assertRaises(LibraryError):
            self.lib.issue_book("LIB2025005", "ACC-0003")


class Returning(Base):
    def test_on_time_return_no_fine(self):
        self.lib.issue_book("LIB2025007", "ACC-0002")
        self.assertEqual(self.lib.return_book("ACC-0002"), 0)
        self.assertEqual(self.status("ACC-0002"), "AVAILABLE")
        self.assertEqual(self.one("SELECT COUNT(*) n FROM fine")["n"], 7)

    def test_late_return_makes_fine(self):
        # ACC-0001 is 6 days overdue with a student, rate Rs 2 per day
        fine = self.lib.return_book("ACC-0001")
        self.assertEqual(fine, Decimal("12.00"))
        row = self.one("SELECT days_late, amount FROM fine ORDER BY fine_id DESC LIMIT 1")
        self.assertEqual((row["days_late"], row["amount"]), (6, Decimal("12.00")))

    def test_return_of_book_not_on_loan(self):
        with self.assertRaises(LibraryError):
            self.lib.return_book("ACC-0002")

    def test_return_before_issue_date_refused(self):
        with self.assertRaises(LibraryError):
            self.lib.return_book("ACC-0001", today=TODAY - timedelta(days=100))

    def test_check_constraint_on_dates(self):
        cur = self.conn.cursor()
        with self.assertRaises(mysql.connector.Error):
            cur.execute("INSERT INTO issue (copy_id, member_id, issue_date, due_date) "
                        "VALUES (2, 7, CURDATE(), DATE_SUB(CURDATE(), INTERVAL 1 DAY))")
        self.conn.rollback()

    def test_renew(self):
        self.lib.issue_book("LIB2025007", "ACC-0002")
        self.assertEqual(self.lib.renew_book("ACC-0002"), TODAY + timedelta(days=28))
        with self.assertRaises(LibraryError):         # overdue copy
            self.lib.renew_book("ACC-0001")


class Reservations(Base):
    ISBN_CLEAN_CODE = "9780132350884"     # 3 copies: two out, one on shelf
    ISBN_WINGS = "9788173711466"

    def test_cannot_reserve_when_copy_on_shelf(self):
        with self.assertRaises(LibraryError):
            self.lib.reserve("LIB2025001", self.ISBN_CLEAN_CODE)

    def test_queue_numbers_and_promotion_on_return(self):
        self.lib.issue_book("LIB2025006", "ACC-0015")           # last copy goes out
        q1 = self.lib.reserve("LIB2025001", self.ISBN_CLEAN_CODE)
        q2 = self.lib.reserve("LIB2025003", self.ISBN_CLEAN_CODE)
        self.assertEqual(q2, q1 + 1)
        self.lib.return_book("ACC-0013")                         # Karan returns
        first = self.one("SELECT status, copy_id FROM reservation WHERE queue_no=%s "
                         "AND edition_id=6", (q1,))
        self.assertEqual(first["status"], "READY")
        self.assertEqual(self.status("ACC-0013"), "ON_HOLD")
        # second person is still waiting
        self.assertEqual(self.one("SELECT status FROM reservation WHERE queue_no=%s AND edition_id=6",
                                  (q2,))["status"], "WAITING")

    def test_held_copy_only_for_the_right_member(self):
        # ACC-0029 is kept for Vikram (LIB2025007) in the sample data
        with self.assertRaises(LibraryError):
            self.lib.issue_book("LIB2025005", "ACC-0029")
        self.lib.issue_book("LIB2025007", "ACC-0029")
        self.assertEqual(self.one("SELECT status FROM reservation WHERE queue_no=3 AND edition_id=13")["status"],
                         "FULFILLED")

    def test_double_reservation_refused(self):
        self.lib.reserve("LIB2025001", self.ISBN_WINGS)          # Aarav is not in the queue yet
        with self.assertRaises(LibraryError):
            self.lib.reserve("LIB2025001", self.ISBN_WINGS)

    def test_cancel_ready_passes_copy_to_next(self):
        rid = self.one("SELECT reservation_id id FROM reservation WHERE status='READY'")["id"]
        self.lib.cancel_reservation(rid)
        nxt = self.one("SELECT status, copy_id FROM reservation WHERE queue_no=4 AND edition_id=13")
        self.assertEqual(nxt["status"], "READY")
        self.assertEqual(self.status("ACC-0029"), "ON_HOLD")

    def test_cancel_last_ready_frees_copy(self):
        self.conn.cursor().execute("UPDATE reservation SET status='CANCELLED' WHERE status='WAITING'")
        self.conn.commit()
        rid = self.one("SELECT reservation_id id FROM reservation WHERE status='READY'")["id"]
        self.lib.cancel_reservation(rid)
        self.assertEqual(self.status("ACC-0029"), "AVAILABLE")

    def test_queue_number_unique_in_database(self):
        cur = self.conn.cursor()
        with self.assertRaises(mysql.connector.Error):
            cur.execute("INSERT INTO reservation (edition_id, member_id, queue_no) VALUES (13, 1, 4)")
        self.conn.rollback()


class Fines(Base):
    def test_partial_then_full_payment(self):
        fid = self.one("SELECT fine_id FROM fine WHERE issue_id=12")["fine_id"]   # Rs 25 unpaid
        self.assertEqual(self.lib.pay_fine(fid, "10"), Decimal("15.00"))
        self.assertEqual(self.lib.pay_fine(fid, "15"), Decimal("0.00"))
        with self.assertRaises(LibraryError):
            self.lib.pay_fine(fid, "1")

    def test_overpay_and_bad_amount(self):
        fid = self.one("SELECT fine_id FROM fine WHERE issue_id=12")["fine_id"]
        for bad in ("100", "-5", "0", "abc"):
            with self.assertRaises(LibraryError):
                self.lib.pay_fine(fid, bad)

    def test_database_blocks_negative_fine(self):
        cur = self.conn.cursor()
        with self.assertRaises(mysql.connector.Error):
            cur.execute("INSERT INTO fine (issue_id, days_late, amount) VALUES (1, 1, -5)")
        self.conn.rollback()

    def test_database_blocks_overpaid_fine(self):
        cur = self.conn.cursor()
        with self.assertRaises(mysql.connector.Error):
            cur.execute("UPDATE fine SET paid_amount = amount + 1 WHERE fine_id = 1")
        self.conn.rollback()


class MembersAndDigital(Base):
    def test_register_member(self):
        self.lib.register_member("LIB3001", "New Person", "new@mail.com", "9876543210", "PUBLIC")
        self.assertEqual(len(self.lib.find_members("New Person")), 1)

    def test_duplicate_email_refused(self):
        with self.assertRaises(LibraryError):
            self.lib.register_member("LIB3002", "Other", "aarav.sharma@college.edu", "", "STUDENT")

    def test_digital_access_and_expired_licence(self):
        self.lib.log_digital_access("LIB2025001", 1, 30)
        with self.assertRaises(LibraryError):
            self.lib.log_digital_access("LIB2025001", 6, 30)      # licence ended
        with self.assertRaises(LibraryError):
            self.lib.log_digital_access("LIB2025001", 1, -4)

    def test_member_history(self):
        rows = library.member_history(self.lib, "LIB2025001")
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[0]["loan_status"], "ON LOAN")


class Reports(Base):
    def test_every_report_runs(self):
        for name, sql in library.REPORTS.items():
            with self.subTest(report=name):
                self.assertIsInstance(self.lib.rows(sql), list)

    def test_overdue_report_values(self):
        rows = self.lib.rows(library.REPORTS["Overdue copies"])
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["days_overdue"], 11)


if __name__ == "__main__":
    unittest.main()
