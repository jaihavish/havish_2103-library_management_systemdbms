"""Database layer for the library system.

All the circulation rules live here, so the screen code (app.py) and the
tests (tests/test_library.py) use exactly the same functions.
Every action that changes more than one table runs inside one transaction.
"""
import os
import re
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal

import mysql.connector
from mysql.connector import errors

FINE_BLOCK_LIMIT = Decimal("50.00")   # no new issues when unpaid fines pass this


class LibraryError(Exception):
    """Raised for any rule break or bad input. The message is shown to the user."""


def connect(password=None):
    return mysql.connector.connect(
        host=os.environ.get("LIB_DB_HOST", "localhost"),
        port=int(os.environ.get("LIB_DB_PORT", "3306")),
        user=os.environ.get("LIB_DB_USER", "root"),
        password=password if password is not None else os.environ.get("LIB_DB_PASSWORD", ""),
        database=os.environ.get("LIB_DB_NAME", "library_db"),
        autocommit=False,
    )


# ---------- input checks ----------

def need_text(value, label, max_len=100):
    value = (value or "").strip()
    if not value:
        raise LibraryError(f"{label} cannot be empty.")
    if len(value) > max_len:
        raise LibraryError(f"{label} is too long (max {max_len} characters).")
    return value


def check_isbn(isbn):
    isbn = (isbn or "").replace("-", "").strip()
    if not re.fullmatch(r"\d{13}", isbn):
        raise LibraryError("ISBN must have exactly 13 digits.")
    return isbn


def check_email(email):
    email = (email or "").strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise LibraryError("Email address is not valid.")
    return email


def check_phone(phone):
    phone = (phone or "").strip()
    if phone and not re.fullmatch(r"\d{10}", phone):
        raise LibraryError("Phone number must have 10 digits.")
    return phone or None


def check_int(value, label, low, high):
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise LibraryError(f"{label} must be a whole number.")
    if not low <= n <= high:
        raise LibraryError(f"{label} must be between {low} and {high}.")
    return n


class Library:
    def __init__(self, conn):
        self.conn = conn

    # ----- helpers -----

    @contextmanager
    def tx(self):
        """One transaction: commit if the block works, roll back if not."""
        if self.conn.in_transaction:
            self.conn.rollback()
        self.conn.start_transaction()
        cur = self.conn.cursor(dictionary=True)
        try:
            yield cur
            self.conn.commit()
        except (errors.IntegrityError, errors.DatabaseError) as e:
            self.conn.rollback()
            # 3819 is a CHECK constraint failure; other database errors pass through
            if isinstance(e, errors.IntegrityError) or e.errno == 3819:
                raise LibraryError(f"Database rule failed: {e.msg}")
            raise
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def rows(self, sql, params=()):
        cur = self.conn.cursor(dictionary=True)
        try:
            cur.execute(sql, params)
            out = cur.fetchall()
        finally:
            cur.close()
        self.conn.rollback()      # end the read so the next one sees fresh data
        return out

    def _member(self, cur, card_no, lock=False):
        cur.execute("SELECT m.*, p.max_books, p.loan_days, p.fine_per_day "
                    "FROM member m JOIN member_policy p ON p.member_type = m.member_type "
                    "WHERE m.card_no = %s" + (" FOR UPDATE" if lock else ""),
                    (need_text(card_no, "Card number", 12),))
        m = cur.fetchone()
        if not m:
            raise LibraryError("No member with that card number.")
        return m

    def _edition_by_isbn(self, cur, isbn):
        cur.execute("SELECT * FROM edition WHERE isbn = %s", (check_isbn(isbn),))
        e = cur.fetchone()
        if not e:
            raise LibraryError("No book with that ISBN in the catalogue.")
        return e

    @staticmethod
    def _check_member_ok(m, today):
        if m["status"] != "ACTIVE":
            raise LibraryError(f"Membership is {m['status'].lower()}.")
        if m["expiry_date"] < today:
            raise LibraryError("Membership has expired.")

    @staticmethod
    def _next_in_line(cur, edition_id):
        cur.execute("SELECT reservation_id FROM reservation "
                    "WHERE edition_id = %s AND status = 'WAITING' "
                    "ORDER BY queue_no LIMIT 1 FOR UPDATE", (edition_id,))
        return cur.fetchone()

    def _free_copy(self, cur, copy_id, edition_id, today):
        """A copy is free again: give it to the next person in line, or put it back."""
        nxt = self._next_in_line(cur, edition_id)
        if nxt:
            cur.execute("UPDATE reservation SET status='READY', copy_id=%s, ready_on=%s "
                        "WHERE reservation_id=%s", (copy_id, today, nxt["reservation_id"]))
            cur.execute("UPDATE copy SET status='ON_HOLD' WHERE copy_id=%s", (copy_id,))
        else:
            cur.execute("UPDATE copy SET status='AVAILABLE' WHERE copy_id=%s", (copy_id,))

    # ----- catalogue -----

    def categories(self):
        return self.rows("SELECT category_id, name FROM category ORDER BY name")

    def add_book(self, title, category_id, authors, publisher, isbn,
                 edition_no=1, pub_year=None, pages=None):
        title = need_text(title, "Title", 200)
        publisher = need_text(publisher, "Publisher")
        isbn = check_isbn(isbn)
        names = [a.strip() for a in (authors or "").split(",") if a.strip()]
        if not names:
            raise LibraryError("Give at least one author (separate several with commas).")
        edition_no = check_int(edition_no, "Edition number", 1, 100)
        pub_year = check_int(pub_year, "Publication year", 1450, date.today().year + 1)
        pages = check_int(pages, "Pages", 1, 20000) if str(pages or "").strip() else None
        with self.tx() as cur:
            cur.execute("SELECT 1 FROM edition WHERE isbn = %s", (isbn,))
            if cur.fetchone():
                raise LibraryError("This ISBN is already in the catalogue.")
            cur.execute("INSERT IGNORE INTO publisher (name) VALUES (%s)", (publisher,))
            cur.execute("SELECT publisher_id FROM publisher WHERE name = %s", (publisher,))
            pub_id = cur.fetchone()["publisher_id"]
            # same title and publisher and edition = same book, so reuse the title row
            cur.execute("SELECT book_id FROM book WHERE title = %s AND category_id = %s",
                        (title, category_id))
            row = cur.fetchone()
            if row:
                book_id = row["book_id"]
            else:
                cur.execute("INSERT INTO book (title, category_id) VALUES (%s, %s)",
                            (title, category_id))
                book_id = cur.lastrowid
                for n in names:
                    cur.execute("SELECT author_id FROM author WHERE name = %s", (n,))
                    a = cur.fetchone()
                    if a:
                        aid = a["author_id"]
                    else:
                        cur.execute("INSERT INTO author (name) VALUES (%s)", (n,))
                        aid = cur.lastrowid
                    cur.execute("INSERT IGNORE INTO book_author VALUES (%s, %s)", (book_id, aid))
            cur.execute("INSERT INTO edition (book_id, publisher_id, isbn, edition_no, pub_year, pages) "
                        "VALUES (%s,%s,%s,%s,%s,%s)",
                        (book_id, pub_id, isbn, edition_no, pub_year, pages))
        return isbn

    def add_copy(self, isbn, accession_no, shelf=""):
        accession_no = need_text(accession_no, "Accession number", 15)
        with self.tx() as cur:
            ed = self._edition_by_isbn(cur, isbn)
            cur.execute("INSERT INTO copy (edition_id, accession_no, shelf) VALUES (%s,%s,%s)",
                        (ed["edition_id"], accession_no, shelf.strip() or None))

    def remove_copy(self, accession_no):
        """Withdraw a copy from the shelf. History is kept, so nothing is deleted."""
        with self.tx() as cur:
            cur.execute("SELECT * FROM copy WHERE accession_no=%s FOR UPDATE", (accession_no.strip(),))
            c = cur.fetchone()
            if not c:
                raise LibraryError("No copy with that accession number.")
            if c["status"] in ("ISSUED", "ON_HOLD"):
                raise LibraryError(f"Copy is {c['status']}; cannot withdraw it now.")
            cur.execute("UPDATE copy SET status='WITHDRAWN' WHERE copy_id=%s", (c["copy_id"],))

    def search(self, text):
        text = need_text(text, "Search text")
        like = f"%{text}%"
        return self.rows(
            "SELECT b.title, GROUP_CONCAT(DISTINCT a.name SEPARATOR ', ') AS authors, "
            "       e.isbn, e.edition_no, c.name AS category, "
            "       (SELECT COUNT(*) FROM copy x WHERE x.edition_id = e.edition_id "
            "          AND x.status = 'AVAILABLE') AS available, "
            "       (SELECT COUNT(*) FROM copy x WHERE x.edition_id = e.edition_id "
            "          AND x.status <> 'WITHDRAWN') AS total_copies "
            "FROM book b "
            "JOIN category c ON c.category_id = b.category_id "
            "JOIN edition e ON e.book_id = b.book_id "
            "JOIN book_author ba ON ba.book_id = b.book_id "
            "JOIN author a ON a.author_id = ba.author_id "
            "WHERE b.title LIKE %s OR a.name LIKE %s OR e.isbn = %s OR c.name LIKE %s "
            "GROUP BY e.edition_id, b.title, e.isbn, e.edition_no, c.name "
            "ORDER BY b.title", (like, like, text, like))

    # ----- members -----

    def register_member(self, card_no, name, email, phone, member_type="STUDENT", years=1, today=None):
        today = today or date.today()
        card_no = need_text(card_no, "Card number", 12)
        name = need_text(name, "Name")
        email = check_email(email)
        phone = check_phone(phone)
        years = check_int(years, "Years", 1, 5)
        with self.tx() as cur:
            cur.execute("SELECT 1 FROM member_policy WHERE member_type=%s", (member_type,))
            if not cur.fetchone():
                raise LibraryError("Unknown member type.")
            expiry = today.replace(year=today.year + years) if not (
                today.month == 2 and today.day == 29) else date(today.year + years, 2, 28)
            cur.execute("INSERT INTO member (card_no, full_name, email, phone, member_type, joined_on, expiry_date) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                        (card_no, name, email, phone, member_type, today, expiry))

    def find_members(self, text):
        like = f"%{need_text(text, 'Search text')}%"
        return self.rows("SELECT card_no, full_name, email, member_type, expiry_date, status "
                         "FROM member WHERE full_name LIKE %s OR card_no LIKE %s OR email LIKE %s "
                         "ORDER BY full_name", (like, like, like))

    # ----- circulation -----

    def issue_book(self, card_no, accession_no, staff_id=1, today=None):
        today = today or date.today()
        accession_no = need_text(accession_no, "Accession number", 15)
        with self.tx() as cur:
            m = self._member(cur, card_no, lock=True)
            self._check_member_ok(m, today)

            cur.execute("SELECT COALESCE(SUM(f.amount - f.paid_amount),0) AS owed "
                        "FROM fine f JOIN issue i ON i.issue_id=f.issue_id WHERE i.member_id=%s",
                        (m["member_id"],))
            owed = cur.fetchone()["owed"]
            if owed > FINE_BLOCK_LIMIT:
                raise LibraryError(f"Member owes Rs {owed}. Fines must be paid first.")

            cur.execute("SELECT COUNT(*) AS n FROM issue WHERE member_id=%s AND return_date IS NULL",
                        (m["member_id"],))
            if cur.fetchone()["n"] >= m["max_books"]:
                raise LibraryError(f"Limit reached: {m['member_type'].title()} members can hold "
                                   f"{m['max_books']} books.")

            cur.execute("SELECT * FROM copy WHERE accession_no=%s FOR UPDATE", (accession_no,))
            c = cur.fetchone()
            if not c:
                raise LibraryError("No copy with that accession number.")

            hold = None
            if c["status"] == "ON_HOLD":
                cur.execute("SELECT * FROM reservation WHERE copy_id=%s AND status='READY' FOR UPDATE",
                            (c["copy_id"],))
                hold = cur.fetchone()
                if not hold or hold["member_id"] != m["member_id"]:
                    raise LibraryError("This copy is kept aside for another member.")
            elif c["status"] != "AVAILABLE":
                raise LibraryError(f"This copy is not available (status: {c['status']}).")

            # A member's own live reservation on this title is used up by the issue
            if hold is None:
                cur.execute("SELECT reservation_id FROM reservation WHERE edition_id=%s "
                            "AND member_id=%s AND status='WAITING'",
                            (c["edition_id"], m["member_id"]))
                waiting = cur.fetchone()
                if waiting:
                    cur.execute("UPDATE reservation SET status='FULFILLED' WHERE reservation_id=%s",
                                (waiting["reservation_id"],))
            else:
                cur.execute("UPDATE reservation SET status='FULFILLED' WHERE reservation_id=%s",
                            (hold["reservation_id"],))

            due = today + timedelta(days=m["loan_days"])
            cur.execute("INSERT INTO issue (copy_id, member_id, issued_by, issue_date, due_date) "
                        "VALUES (%s,%s,%s,%s,%s)", (c["copy_id"], m["member_id"], staff_id, today, due))
            cur.execute("UPDATE copy SET status='ISSUED' WHERE copy_id=%s", (c["copy_id"],))
        return due

    def return_book(self, accession_no, today=None):
        """Returns the fine amount (0 if on time)."""
        today = today or date.today()
        accession_no = need_text(accession_no, "Accession number", 15)
        with self.tx() as cur:
            cur.execute("SELECT i.*, c.edition_id, p.fine_per_day "
                        "FROM issue i JOIN copy c ON c.copy_id=i.copy_id "
                        "JOIN member m ON m.member_id=i.member_id "
                        "JOIN member_policy p ON p.member_type=m.member_type "
                        "WHERE c.accession_no=%s AND i.return_date IS NULL FOR UPDATE", (accession_no,))
            i = cur.fetchone()
            if not i:
                raise LibraryError("That copy is not out on loan.")
            if today < i["issue_date"]:
                raise LibraryError("Return date cannot be before the issue date.")
            cur.execute("UPDATE issue SET return_date=%s WHERE issue_id=%s", (today, i["issue_id"]))
            late = max((today - i["due_date"]).days, 0)
            fine = Decimal(late) * i["fine_per_day"]
            if late:
                cur.execute("INSERT INTO fine (issue_id, days_late, amount, assessed_on) "
                            "VALUES (%s,%s,%s,%s)", (i["issue_id"], late, fine, today))
            self._free_copy(cur, i["copy_id"], i["edition_id"], today)
        return fine

    def renew_book(self, accession_no, today=None):
        """Extend the loan by one loan period. Not allowed if someone is waiting."""
        today = today or date.today()
        with self.tx() as cur:
            cur.execute("SELECT i.issue_id, i.due_date, c.edition_id, p.loan_days "
                        "FROM issue i JOIN copy c ON c.copy_id=i.copy_id "
                        "JOIN member m ON m.member_id=i.member_id "
                        "JOIN member_policy p ON p.member_type=m.member_type "
                        "WHERE c.accession_no=%s AND i.return_date IS NULL FOR UPDATE",
                        (need_text(accession_no, "Accession number", 15),))
            i = cur.fetchone()
            if not i:
                raise LibraryError("That copy is not out on loan.")
            if i["due_date"] < today:
                raise LibraryError("Overdue books cannot be renewed. Return it first.")
            if self._next_in_line(cur, i["edition_id"]):
                raise LibraryError("Someone has reserved this title, so it cannot be renewed.")
            new_due = i["due_date"] + timedelta(days=i["loan_days"])
            cur.execute("UPDATE issue SET due_date=%s WHERE issue_id=%s", (new_due, i["issue_id"]))
        return new_due

    # ----- reservations -----

    def reserve(self, card_no, isbn, today=None):
        today = today or date.today()
        with self.tx() as cur:
            m = self._member(cur, card_no, lock=True)
            self._check_member_ok(m, today)
            ed = self._edition_by_isbn(cur, isbn)
            cur.execute("SELECT COUNT(*) AS n FROM copy WHERE edition_id=%s AND status='AVAILABLE'",
                        (ed["edition_id"],))
            if cur.fetchone()["n"]:
                raise LibraryError("A copy is on the shelf. Issue it directly instead of reserving.")
            cur.execute("SELECT COUNT(*) AS n FROM copy WHERE edition_id=%s "
                        "AND status IN ('ISSUED','ON_HOLD')", (ed["edition_id"],))
            if not cur.fetchone()["n"]:
                raise LibraryError("This title has no copies that can be reserved.")
            cur.execute("SELECT 1 FROM reservation WHERE edition_id=%s AND member_id=%s "
                        "AND status IN ('WAITING','READY')", (ed["edition_id"], m["member_id"]))
            if cur.fetchone():
                raise LibraryError("You already have a reservation for this title.")
            cur.execute("SELECT 1 FROM issue i JOIN copy c ON c.copy_id=i.copy_id "
                        "WHERE i.member_id=%s AND i.return_date IS NULL AND c.edition_id=%s",
                        (m["member_id"], ed["edition_id"]))
            if cur.fetchone():
                raise LibraryError("You already have this edition on loan.")
            # lock the edition's reservation rows so two people cannot take the same number
            cur.execute("SELECT COALESCE(MAX(queue_no),0)+1 AS q FROM reservation "
                        "WHERE edition_id=%s FOR UPDATE", (ed["edition_id"],))
            q = cur.fetchone()["q"]
            cur.execute("INSERT INTO reservation (edition_id, member_id, queue_no) VALUES (%s,%s,%s)",
                        (ed["edition_id"], m["member_id"], q))
        return q

    def cancel_reservation(self, reservation_id, today=None):
        today = today or date.today()
        with self.tx() as cur:
            cur.execute("SELECT * FROM reservation WHERE reservation_id=%s FOR UPDATE", (reservation_id,))
            r = cur.fetchone()
            if not r or r["status"] not in ("WAITING", "READY"):
                raise LibraryError("No live reservation with that number.")
            cur.execute("UPDATE reservation SET status='CANCELLED', copy_id=NULL WHERE reservation_id=%s",
                        (reservation_id,))
            if r["status"] == "READY":
                self._free_copy(cur, r["copy_id"], r["edition_id"], today)

    def reservations(self):
        return self.rows("SELECT reservation_id, title, position_in_line, full_name, status, reserved_on "
                         "FROM v_reservation_queue ORDER BY title, position_in_line")

    # ----- fines -----

    def fines_for(self, card_no):
        return self.rows(
            "SELECT f.fine_id, b.title, i.due_date, i.return_date, f.days_late, f.amount, "
            "       f.paid_amount, f.amount - f.paid_amount AS balance "
            "FROM fine f JOIN issue i ON i.issue_id=f.issue_id "
            "JOIN member m ON m.member_id=i.member_id "
            "JOIN copy c ON c.copy_id=i.copy_id JOIN edition e ON e.edition_id=c.edition_id "
            "JOIN book b ON b.book_id=e.book_id WHERE m.card_no=%s ORDER BY f.fine_id",
            (need_text(card_no, "Card number", 12),))

    def pay_fine(self, fine_id, amount, today=None):
        today = today or date.today()
        try:
            amount = Decimal(str(amount).strip())
        except Exception:
            raise LibraryError("Amount must be a number.")
        if amount <= 0:
            raise LibraryError("Amount must be more than zero.")
        with self.tx() as cur:
            cur.execute("SELECT * FROM fine WHERE fine_id=%s FOR UPDATE", (fine_id,))
            f = cur.fetchone()
            if not f:
                raise LibraryError("No fine with that number.")
            balance = f["amount"] - f["paid_amount"]
            if balance == 0:
                raise LibraryError("This fine is already paid.")
            if amount > balance:
                raise LibraryError(f"Amount is more than the balance of Rs {balance}.")
            cur.execute("UPDATE fine SET paid_amount = paid_amount + %s, paid_on = %s WHERE fine_id=%s",
                        (amount, today, fine_id))
        return balance - amount

    # ----- digital resources -----

    def digital_resources(self):
        return self.rows("SELECT resource_id, title, resource_type, url, licence_end "
                         "FROM digital_resource ORDER BY title")

    def log_digital_access(self, card_no, resource_id, minutes, today=None):
        today = today or date.today()
        minutes = check_int(minutes, "Minutes", 0, 1440)
        with self.tx() as cur:
            m = self._member(cur, card_no)
            self._check_member_ok(m, today)
            cur.execute("SELECT licence_end FROM digital_resource WHERE resource_id=%s", (resource_id,))
            r = cur.fetchone()
            if not r:
                raise LibraryError("No such digital resource.")
            if r["licence_end"] and r["licence_end"] < today:
                raise LibraryError("The licence for this resource has ended.")
            cur.execute("INSERT INTO digital_access_log (resource_id, member_id, minutes_used) "
                        "VALUES (%s,%s,%s)", (resource_id, m["member_id"], minutes))


# ---------- lists and numbers for the screens ----------

def dashboard_stats(lib):
    q = lambda sql: list(lib.rows(sql)[0].values())[0]
    return {
        "Titles": q("SELECT COUNT(*) FROM book"),
        "Copies on shelf": q("SELECT COUNT(*) FROM copy WHERE status='AVAILABLE'"),
        "Books on loan": q("SELECT COUNT(*) FROM issue WHERE return_date IS NULL"),
        "Overdue": q("SELECT COUNT(*) FROM v_overdue_copies"),
        "Active members": q("SELECT COUNT(*) FROM member WHERE status='ACTIVE' AND expiry_date >= CURDATE()"),
        "Waiting reservations": q("SELECT COUNT(*) FROM reservation WHERE status IN ('WAITING','READY')"),
        "Unpaid fines (Rs)": q("SELECT COALESCE(SUM(amount - paid_amount),0) FROM fine"),
        "Digital visits": q("SELECT COUNT(*) FROM digital_access_log"),
    }


def member_choices(lib):
    return lib.rows("SELECT card_no, full_name, member_type FROM member "
                    "WHERE status='ACTIVE' AND expiry_date >= CURDATE() ORDER BY full_name")


def available_copies(lib):
    return lib.rows("SELECT cp.accession_no, b.title FROM copy cp "
                    "JOIN edition e ON e.edition_id=cp.edition_id JOIN book b ON b.book_id=e.book_id "
                    "WHERE cp.status IN ('AVAILABLE','ON_HOLD') ORDER BY b.title, cp.accession_no")


def loans_out(lib):
    return lib.rows("SELECT cp.accession_no, b.title, m.full_name AS member, m.card_no, "
                    "i.issue_date, i.due_date, "
                    "GREATEST(DATEDIFF(CURDATE(), i.due_date), 0) AS days_late "
                    "FROM issue i JOIN copy cp ON cp.copy_id=i.copy_id "
                    "JOIN edition e ON e.edition_id=cp.edition_id JOIN book b ON b.book_id=e.book_id "
                    "JOIN member m ON m.member_id=i.member_id "
                    "WHERE i.return_date IS NULL ORDER BY i.due_date")


def reservable_editions(lib):
    """Editions with no copy on the shelf but at least one copy out."""
    return lib.rows("SELECT e.isbn, b.title, e.edition_no FROM edition e JOIN book b ON b.book_id=e.book_id "
                    "WHERE NOT EXISTS (SELECT 1 FROM copy c WHERE c.edition_id=e.edition_id AND c.status='AVAILABLE') "
                    "AND EXISTS (SELECT 1 FROM copy c WHERE c.edition_id=e.edition_id "
                    "            AND c.status IN ('ISSUED','ON_HOLD')) ORDER BY b.title")


def all_members(lib):
    return lib.rows("SELECT card_no, full_name, email, phone, member_type, expiry_date, status "
                    "FROM member ORDER BY full_name")


def all_fines(lib, unpaid_only=False):
    return lib.rows("SELECT f.fine_id, m.full_name AS member, m.card_no, b.title, f.days_late, "
                    "f.amount, f.paid_amount, f.amount - f.paid_amount AS balance "
                    "FROM fine f JOIN issue i ON i.issue_id=f.issue_id JOIN member m ON m.member_id=i.member_id "
                    "JOIN copy c ON c.copy_id=i.copy_id JOIN edition e ON e.edition_id=c.edition_id "
                    "JOIN book b ON b.book_id=e.book_id "
                    + ("WHERE f.amount > f.paid_amount " if unpaid_only else "") + "ORDER BY f.fine_id DESC")


def reservations_live(lib):
    return lib.rows("SELECT reservation_id, title, position_in_line, full_name, status, reserved_on "
                    "FROM v_reservation_queue ORDER BY title, position_in_line")


def catalogue(lib):
    return lib.rows("SELECT b.title, GROUP_CONCAT(DISTINCT a.name SEPARATOR ', ') AS authors, "
                    "e.isbn, e.edition_no, c.name AS category, "
                    "(SELECT COUNT(*) FROM copy x WHERE x.edition_id=e.edition_id AND x.status='AVAILABLE') AS available, "
                    "(SELECT COUNT(*) FROM copy x WHERE x.edition_id=e.edition_id AND x.status<>'WITHDRAWN') AS copies "
                    "FROM book b JOIN category c ON c.category_id=b.category_id "
                    "JOIN edition e ON e.book_id=b.book_id JOIN book_author ba ON ba.book_id=b.book_id "
                    "JOIN author a ON a.author_id=ba.author_id "
                    "GROUP BY e.edition_id, b.title, e.isbn, e.edition_no, c.name ORDER BY b.title")


# ---------- reports used by the front end ----------

REPORTS = {
    "Available titles":
        "SELECT title, edition_no, authors, copies_available FROM v_available_titles ORDER BY title",
    "Overdue copies":
        "SELECT accession_no, title, full_name, due_date, days_overdue, fine_so_far "
        "FROM v_overdue_copies ORDER BY days_overdue DESC",
    "Popular books":
        "SELECT title, times_issued FROM v_popular_books ORDER BY times_issued DESC, title LIMIT 10",
    "Reservation queue":
        "SELECT title, position_in_line, full_name, status, reserved_on "
        "FROM v_reservation_queue ORDER BY title, position_in_line",
    "Fine collection by month":
        "SELECT month, fines_raised, total_fined, total_collected, still_pending "
        "FROM v_fine_summary ORDER BY month",
    "Books currently on loan":
        "SELECT cp.accession_no, b.title, m.full_name, i.issue_date, i.due_date "
        "FROM issue i JOIN copy cp ON cp.copy_id=i.copy_id JOIN edition e ON e.edition_id=cp.edition_id "
        "JOIN book b ON b.book_id=e.book_id JOIN member m ON m.member_id=i.member_id "
        "WHERE i.return_date IS NULL ORDER BY i.due_date",
    "Digital resource usage":
        "SELECT d.title, d.resource_type, COUNT(l.log_id) AS visits, "
        "COALESCE(SUM(l.minutes_used),0) AS total_minutes "
        "FROM digital_resource d LEFT JOIN digital_access_log l ON l.resource_id=d.resource_id "
        "GROUP BY d.resource_id, d.title, d.resource_type ORDER BY visits DESC",
}


def member_history(lib, card_no):
    return lib.rows("SELECT title, accession_no, issue_date, due_date, return_date, loan_status, fine_amount "
                    "FROM v_member_history WHERE card_no=%s ORDER BY issue_date DESC",
                    (need_text(card_no, "Card number", 12),))
