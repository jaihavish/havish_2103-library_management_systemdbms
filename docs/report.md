# Library Circulation and Digital Resource Management System

Project 02 – Database Management Systems

---

## 1. Why this project

A small library usually starts with a register and a few Excel sheets. It works until the library grows. Then the same questions keep coming up and nobody can answer them quickly. Is this book on the shelf? Who has had it for a month? How much fine does that student owe? Who is next in line for the book everybody wants?

This project replaces the registers with one MySQL database and a small desktop program. The database keeps the data clean and refuses wrong entries. The program lets the library staff do their daily work without writing any SQL.

I used MySQL 8.0 for the database and Python (Tkinter and `mysql-connector-python`) for the front end.

## 2. What the system has to do

**Who uses it**

| Role | What they do |
|---|---|
| Librarian | Adds books and copies, registers members, issues and returns books, takes fine payments, handles reservations |
| Admin | Same as librarian, and looks at the reports |
| Member (student, faculty, public) | Borrows, reserves and uses digital resources. They do not log in yet; the librarian acts for them at the desk |

**Main requirements**

1. Keep a catalogue of titles, editions, authors, publishers and categories.
2. Track each physical copy by its accession number.
3. Register members. Different member types get different limits.
4. Issue and return books, and know exactly which copies are out.
5. Let members reserve a title when every copy is out, and serve the queue in order.
6. Work out fines for late returns and record payments.
7. Record who uses the digital resources (e-books, journals, videos).
8. Give reports: available titles, overdue copies, member history, popular books, reservations, fine collection.

**Loan rules I chose** (stored in the `member_policy` table so the library can change them without touching the code)

| Member type | Books at a time | Loan days | Fine per late day |
|---|---|---|---|
| Student | 3 | 14 | Rs 2 |
| Faculty | 6 | 30 | Rs 1 |
| Public | 2 | 7 | Rs 5 |

A member with more than Rs 50 of unpaid fine cannot borrow until some of it is paid.

## 3. Conceptual design (ER model)

### 3.1 Entities

| Entity | Key attributes |
|---|---|
| Publisher | name, city |
| Author | name, country |
| Category | name |
| Book (the title) | title, category |
| Edition | ISBN, edition number, year, pages |
| Copy | accession number, shelf, status |
| Member | card number, name, email, phone, type, expiry date, status |
| Member policy | member type, max books, loan days, fine per day |
| Staff | username, name, role |
| Issue | issue date, due date, return date |
| Reservation | queue number, reserved on, status |
| Fine | days late, amount, paid amount |
| Digital resource | title, type, URL, licence end |
| Digital access log | time, minutes used |

I split *Book*, *Edition* and *Copy* on purpose. "Database System Concepts" is one title. It has a 6th and a 7th edition, each with its own ISBN. The library may own three physical copies of the 6th edition, and each copy has its own accession number. If all of this sat in one table, the title and publisher would repeat on every copy row.

### 3.2 Relationships

* A **category** has many **books**; each book is in one category (1 : N).
* A **book** is written by many **authors**, and an author writes many books (M : N, resolved with `book_author`).
* A **book** has many **editions**; an edition belongs to one book and one publisher (1 : N).
* An **edition** has many **copies** (1 : N).
* A **member** takes many **issues**; a **copy** appears in many issues over time, but in only one *active* issue (1 : N each).
* A **member** makes many **reservations**; a reservation is for one **edition**.
* A **late issue** has at most one **fine** (1 : 0..1).
* A **member** has one **member type**, which decides the policy (N : 1).
* A **member** and a **digital resource** are linked many-to-many through **digital access log**.

### 3.3 ER diagram

```
 PUBLISHER 1───< EDITION >───1 BOOK >───1 CATEGORY
                   │ 1          │
                   │            └──< BOOK_AUTHOR >──1 AUTHOR
                   ^ N
                 COPY
                   │ 1
                   ^ N
 STAFF 1───< ISSUE >───1 MEMBER >───1 MEMBER_POLICY
              │ 1         │ 1
              │ 0..1      ^ N
              FINE      RESERVATION >───1 EDITION
                          │
 DIGITAL_RESOURCE 1───< DIGITAL_ACCESS_LOG >───1 MEMBER
        └──> PUBLISHER (optional)
```

(`1───<` means one-to-many, `>───1` means many-to-one.)

## 4. Relational schema

Primary keys are underlined with `PK`, foreign keys with `FK`.

```
publisher(PK publisher_id, name, city)
author(PK author_id, name, country)
category(PK category_id, name)
member_policy(PK member_type, max_books, loan_days, fine_per_day)
staff(PK staff_id, username, full_name, role)

book(PK book_id, title, FK category_id)
book_author(PK/FK book_id, PK/FK author_id)
edition(PK edition_id, FK book_id, FK publisher_id, isbn, edition_no, pub_year, pages)
copy(PK copy_id, FK edition_id, accession_no, shelf, status, added_on)

member(PK member_id, card_no, full_name, email, phone, FK member_type,
       joined_on, expiry_date, status)
issue(PK issue_id, FK copy_id, FK member_id, FK issued_by, issue_date, due_date, return_date)
reservation(PK reservation_id, FK edition_id, FK member_id, queue_no, reserved_on,
            status, FK copy_id, ready_on)
fine(PK fine_id, FK issue_id, days_late, amount, paid_amount, assessed_on, paid_on)

digital_resource(PK resource_id, title, resource_type, FK publisher_id, url, licence_end)
digital_access_log(PK log_id, FK resource_id, FK member_id, accessed_at, minutes_used)
```

The full `CREATE TABLE` statements are in `sql/01_schema.sql`.

## 5. Normalization (up to 3NF)

I started from the sheet a librarian would keep by hand, one wide row per loan:

```
LOAN_SHEET(card_no, member_name, email, member_type, max_books, loan_days, fine_per_day,
           accession_no, shelf, isbn, title, edition_no, authors, publisher, publisher_city,
           category, issue_date, due_date, return_date, fine_amount)
```

**First Normal Form (1NF).** Every column must hold one value, and rows must be identifiable. In the sheet, `authors` holds a list ("Silberschatz, Korth, Sudarshan"). I moved authors into their own table and linked them through `book_author`, so each cell now holds a single value. Each table also got a primary key.

**Second Normal Form (2NF).** No column may depend on only *part* of a composite key. Taking `(card_no, accession_no, issue_date)` as the key of a loan row, the member name depends only on `card_no`, and the title depends only on the copy. I pulled these out into `member`, `copy`, `edition` and `book`, so a loan row now holds only facts about the loan itself (`issue`).

**Third Normal Form (3NF).** No non-key column may depend on another non-key column. Three examples:

| Dependency found | Fix |
|---|---|
| `member_type → max_books, loan_days, fine_per_day` | New table `member_policy` |
| `publisher → publisher_city` | Kept in `publisher` only |
| `book → category`, and `isbn → book, publisher, year` | `book` and `edition` tables |

One more decision: I first thought of storing `member_id` in the `fine` table. But `issue_id → member_id` already, so that would break 3NF. `fine` only keeps `issue_id`, and the member is found by joining to `issue`.

**Final check.** In every table, each non-key column depends on the key, the whole key, and nothing but the key. Two things look like duplicates but are not. `reservation.copy_id` is only filled while a copy is being held for that person, so it describes the reservation. `issue.active_copy_id` is a generated helper column used for a constraint (see 6.1); it is computed by the database and never typed in.

## 6. Business rules and where they are enforced

### 6.1 In the database

| Rule | How |
|---|---|
| ISBN is unique and has 13 digits | `UNIQUE` plus `CHECK (isbn REGEXP '^[0-9]{13}$')` |
| Accession number is unique | `UNIQUE (accession_no)` |
| One active issue per copy | Generated column `active_copy_id = IF(return_date IS NULL, copy_id, NULL)` with a `UNIQUE` index. While a book is out, the value is its copy id. After return it becomes `NULL`, and MySQL allows many `NULL`s in a unique index. So a second active issue for the same copy is rejected, but old history is fine |
| Valid issue and return dates | `CHECK (due_date > issue_date)` and `CHECK (return_date IS NULL OR return_date >= issue_date)` |
| Reservation queue order | `queue_no` plus `UNIQUE (edition_id, live_queue_no)`, where `live_queue_no` is only filled while the status is `WAITING` or `READY`. Two people can never hold the same place in a queue |
| One live reservation per member per title | `UNIQUE (edition_id, live_member_id)` |
| Fines cannot be negative or over-paid | `CHECK (amount >= 0)`, `CHECK (paid_amount >= 0)`, `CHECK (paid_amount <= amount)` |
| Membership dates make sense | `CHECK (expiry_date > joined_on)` |
| Defaults | `status = 'AVAILABLE'`, `edition_no = 1`, `fine_per_day = 2.00`, dates default to today |
| No orphan rows | Foreign keys everywhere |

### 6.2 In the program (`app/library.py`)

These rules need a look at several rows at once, so they are checked in code, inside a transaction:

* member must be active and not expired
* member must be under the book limit for their type
* member must not owe more than Rs 50
* copy must be available, or be held for that same member
* the fine is `days late × rate` and is created at return time
* when a book comes back and someone is waiting, the copy is put on hold for the first person in line

## 7. Transactions, indexes and validation

**Transactions.** Issuing a book changes three things: it inserts the loan, marks the copy as issued, and may close a reservation. Returning a book updates the loan, may insert a fine, and then either puts the copy back on the shelf or holds it for the next person. If any step fails, the whole action is rolled back, so the data never ends up half changed. The code uses `SELECT ... FOR UPDATE` on the member, the copy and the reservation rows, so two librarians working at the same time cannot give the same copy to two people.

**Indexes.** Primary keys, unique columns and foreign keys already have indexes. I added more for columns that are searched often:

| Index | Used for |
|---|---|
| `book(title)` | Title search |
| `author(name)` | Author search |
| `member(full_name)` | Finding a member |
| `copy(edition_id, status)` | Counting available copies per title |
| `issue(due_date, return_date)` | Overdue report |
| `issue(member_id, issue_date)` | Member history |
| `reservation(edition_id, status)` | Reservation queue |
| `digital_access_log(resource_id, accessed_at)` | Usage reports |

`EXPLAIN SELECT * FROM book WHERE title LIKE 'Data%'` shows the title index in use (query Q20 in `sql/04_queries.sql`). With only 15 books the speed gain is not visible, but the index matters when the catalogue grows to thousands.

**Validation.** The program checks input before it reaches the database: empty fields, ISBN length, email format, 10-digit phone numbers, year range, amounts above zero. The database then acts as a second line of defence with its `CHECK`, `UNIQUE` and `FOREIGN KEY` rules. The tests try to break the database directly to prove this.

## 8. Sample data

`sql/02_sample_data.sql` loads:

* 15 titles, 16 editions, 36 copies, 18 authors, 6 publishers, 6 categories
* 12 members (students, faculty, public, one expired)
* 34 loans: 24 returned, 10 still out (5 of them overdue)
* 7 fines, some paid, some part-paid, some unpaid
* a reservation queue for *Wings of Fire* (one done, one cancelled, one ready, two waiting)
* 6 digital resources and 24 access records

Dates are written as "today minus N days", so the overdue and fine reports always have something to show.

## 9. SQL queries, views and reports

`sql/03_views.sql` has six views and `sql/04_queries.sql` has twenty queries.

| Need | Where |
|---|---|
| Available titles | view `v_available_titles` (Q4) |
| Overdue copies and fine so far | view `v_overdue_copies` (Q5) |
| Member history | view `v_member_history` (Q6) |
| Popular books | view `v_popular_books` (Q7) |
| Reservation queue | view `v_reservation_queue` (Q13) |
| Fine collection by month | view `v_fine_summary` (Q14) |
| Joins | Q2, Q3, Q9 |
| Aggregates, GROUP BY, HAVING | Q7, Q8, Q9, Q16, Q19 |
| Nested queries | Q10 (NOT IN), Q11 (subquery in HAVING), Q12 (correlated) |

Output from the sample data, for example, the overdue report:

| Accession | Title | Member | Due | Days overdue | Fine so far |
|---|---|---|---|---|---|
| ACC-0010 | Introduction to Algorithms | Rohan Gupta | 11 days ago | 11 | Rs 22 |
| ACC-0028 | Higher Engineering Mathematics | Dr. Neha Kapoor | 10 days ago | 10 | Rs 10 |
| ACC-0001 | Database System Concepts | Aarav Sharma | 6 days ago | 6 | Rs 12 |

Faculty pay Rs 1 a day, so the faculty member's 10 days cost less than the student's 6 days at Rs 2.

## 10. The front end

`app/app.py` is a desktop program built with Tkinter. It has seven tabs:

| Tab | What it does |
|---|---|
| Search | Find books by title, author, category or ISBN, and see how many copies are on the shelf |
| Catalogue | Add a book, add a copy, withdraw a copy |
| Members | Register a member, search members, see a member's history |
| Issue / Return | Issue, return and renew a book. The fine is shown at return time |
| Reservations | Reserve, cancel, view the queue |
| Fines | Look up a member's fines and record a payment |
| Reports | Run any of the seven circulation reports |

All the rules are in `library.py`, not in the screens. That means the tests and the screens go through the same code. Error messages are written in plain language ("Limit reached: Student members can hold 3 books.").

## 11. Testing

The file `tests/test_library.py` has 40 automated tests. Before each test the database is rebuilt from the three SQL files, so tests do not affect each other. All 40 pass on MySQL 8.0.

| Area | What is checked | Result |
|---|---|---|
| Input | Bad ISBN, empty title, bad email, bad phone, year in the future are refused | Pass |
| Catalogue | New book and copy can be found by search; duplicate ISBN and duplicate accession number refused; search by author works; issued copy cannot be withdrawn | Pass |
| Issue | Due date is 14 days (student) or 30 days (faculty); a copy that is out cannot be issued again; student limit of 3 holds and the failed 4th issue leaves nothing half-done; expired member, unknown member and unknown copy refused; member with a big fine blocked | Pass |
| Database rules | Two active issues for one copy are rejected by MySQL itself; due date before issue date rejected | Pass |
| Return | On-time return gives no fine; 6 days late gives Rs 12; returning a book that is not out is refused; return before issue date refused; renew works and overdue renew is refused | Pass |
| Reservation | Cannot reserve while a copy is on the shelf; queue numbers go up by one; first person in line gets the returned copy; held copy can only be issued to the right member; double reservation refused; cancelling a held copy passes it on or frees it; duplicate queue number rejected by MySQL | Pass |
| Fines | Part payment then full payment; over-payment, zero, negative and text amounts refused; negative fine and over-paid fine rejected by MySQL | Pass |
| Members and digital | Register member; duplicate email refused; expired licence and negative minutes refused; member history shows the right rows | Pass |
| Reports | All seven reports run; overdue report shows 5 rows with the longest first | Pass |

Two bugs found while testing, and fixed:

1. The search screen counted copies twice for books with two authors, because the author join multiplied the rows. I changed the counts to sub-queries.
2. MySQL reports a failed `CHECK` as a general database error, not an integrity error, so the program showed a raw error. The transaction wrapper now catches error code 3819 and shows a clear message.

**What is not tested:** the Tkinter screens are only smoke-tested (the window builds and the queries behind it run). Clicking through every screen was done by hand, not by script.

## 12. Limits and future work

* Members do not log in; the librarian uses the program for them. A web version with member logins would be the next step.
* Fines are assessed only when a book is returned. A nightly job could update overdue amounts.
* A reserved copy waits on hold with no time limit. A real library would expire it after a few days.
* Lost-book charges and fine waivers are not handled.
* The program connects as one database user. A real setup would use separate users for librarian and admin with limited rights.

## 13. How to run

1. Install MySQL 8.0.16 or newer and Python 3 with `mysql-connector-python`.
2. Load the SQL files in order:
   ```
   mysql -u root -p < sql/01_schema.sql
   mysql -u root -p < sql/02_sample_data.sql
   mysql -u root -p < sql/03_views.sql
   ```
3. Start the program from the `app` folder: `python app.py`. If the password is not found it asks for it. Set `LIB_DB_HOST`, `LIB_DB_PORT`, `LIB_DB_USER`, `LIB_DB_PASSWORD` if your setup is different.
4. Run the tests (they rebuild `library_db`): `python -m unittest discover -s tests -v`
