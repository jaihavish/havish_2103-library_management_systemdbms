# Library Circulation and Digital Resource Management System
**Comprehensive Technical Documentation & Project Guide**

---

## 📌 Executive Summary

The **Library Circulation and Digital Resource Management System** is a full-featured relational database management application designed to replace paper registers and uncoordinated spreadsheets in academic and public libraries. 

Built with **MySQL 8.0** and **Python 3**, the system ensures strict relational integrity, ACID-compliant transactions, automated overdue fine computations, multi-tier borrowing policies, hold reservations, and electronic resource tracking. It provides two operational front ends:
1. **Modern Web Interface** (`http://localhost:5000`) powered by Flask, Tailwind CSS, and Chart.js.
2. **Native Desktop GUI** powered by Python Tkinter.

---

## 🎯 Motivation & Objectives

### The Problem
Traditional or spreadsheet-based library management faces common points of failure:
* **Duplicate or Inconsistent Data**: Redundant entries for multi-edition books or multi-author titles.
* **Untracked Copy Inventory**: Inability to differentiate a literary work (title) from specific editions (ISBNs) and individual physical shelf copies (accession numbers).
* **Policy Violations**: Over-borrowing beyond limits or borrowing while carrying unpaid overdue fines.
* **Unstructured Hold Queues**: Manual, subjective reservation lists when books are checked out.
* **Fragmented Digital Assets**: No centralized tracking of electronic books, journals, and digital resource usage.

### System Solution
This system centralizes all catalog, circulation, membership, and digital records in an indexed, normalized MySQL relational database, strictly enforcing business rules directly at both the database and application levels.

---

## 🏗️ Architecture & Technology Stack

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interfaces                        │
├──────────────────────────────┬──────────────────────────────┤
│    Modern Web Application    │      Desktop GUI (Tkinter)   │
│   (Flask, Tailwind, Chart.js)│       (app/app.py - ttk)     │
└──────────────┬───────────────┴──────────────┬───────────────┘
               │                              │
               ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│             Circulation & Business Logic Engine             │
│            (app/library.py & web_app.py REST API)           │
│  - Input Sanitization (ISBN-13, Regex Email/Phone)          │
│  - Multi-tier Borrowing Rules & ₹50 Fine Lock               │
│  - FIFO Reservation Queue & Hold Transitions                │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Relational Database (MySQL 8)               │
│  - InnoDB Engine with Full Foreign Key Constraints         │
│  - Strict CHECK Constraints (Positive Numbers, Enum Roles)  │
│  - Analytical Views (Overdue, Member History, Popularity)   │
│  - Zero-Setup In-Memory Fallback Demo Mode                  │
└─────────────────────────────────────────────────────────────┘
```

### Technology Highlights
* **Database**: MySQL 8.0+ (utilizing InnoDB, transactional integrity, foreign key cascades, and check constraints).
* **Backend Layer**: Python 3.10+ using `mysql-connector-python` with atomic transaction context managers (`tx()`).
* **Web UI**: Flask REST API, responsive Tailwind CSS styling, FontAwesome icons, and Chart.js analytics.
* **Desktop UI**: Python Tkinter with custom ttk theme palettes.
* **Testing**: Python `unittest` suite covering circulation edge cases, borrow limits, fine caps, and transaction rollbacks.

---

## 🗄️ Relational Database Design

### 1. Three-Tier Catalog Normalization
A critical architectural decision is separating a **Book**, an **Edition**, and a **Physical Copy**:

```
[Book] (Title, Category)
   │ 1
   └──< [Edition] (ISBN, Edition No, Year, Pages, Publisher)
          │ 1
          └──< [Copy] (Accession No, Shelf Location, Status)
```

* **`book`**: Represents the intellectual work (e.g., *"Database System Concepts"* in category *"Computer Science"*).
* **`edition`**: Represents a specific publication run with its unique 13-digit ISBN, publication year, publisher, and page count.
* **`copy`**: Represents a physical book sitting on a library shelf, identified by a distinct **Accession Number** (e.g., `ACC-CS-001`). Its status transitions through `AVAILABLE`, `ISSUED`, `ON_HOLD`, `LOST`, or `WITHDRAWN`.

*Benefit*: Eliminates massive data duplication; when a library acquires 5 physical copies of a 7th Edition, the publisher, authors, and title are stored once, not replicated 5 times.

---

### 2. Entity Relationship Summary

| Entity Table | Primary Key | Key Attributes & Foreign Keys | Description |
|---|---|---|---|
| `publisher` | `publisher_id` | `name` (UNIQUE), `city` | Publishing houses |
| `author` | `author_id` | `name`, `country` | Book authors |
| `category` | `category_id` | `name` (UNIQUE) | Academic subject categories |
| `book` | `book_id` | `title`, `category_id` (FK) | Master title record |
| `book_author` | `(book_id, author_id)` | Composite PK | Resolves Many-to-Many book-author relationship |
| `edition` | `edition_id` | `isbn` (UNIQUE 13 digits), `book_id` (FK), `publisher_id` (FK), `edition_no`, `pub_year` | Specific published editions |
| `copy` | `copy_id` | `accession_no` (UNIQUE), `edition_id` (FK), `shelf`, `status` | Physical inventory copies |
| `member_policy` | `member_type` | `max_books`, `loan_days`, `fine_per_day` | Tiered borrowing configuration |
| `member` | `member_id` | `card_no` (UNIQUE), `full_name`, `email`, `phone`, `member_type` (FK), `status` | Registered library patrons |
| `staff` | `staff_id` | `username` (UNIQUE), `full_name`, `role` (`LIBRARIAN` / `ADMIN`) | Library operators |
| `issue` | `issue_id` | `copy_id` (FK), `member_id` (FK), `issued_by` (FK), `issue_date`, `due_date`, `return_date` | Circulation loan records |
| `fine` | `fine_id` | `issue_id` (FK UNIQUE), `days_late`, `amount`, `paid_amount`, `assessed_on` | Penalties assessed on overdue returns |
| `reservation` | `reservation_id` | `edition_id` (FK), `member_id` (FK), `queue_no`, `status`, `copy_id` (FK) | Waitlist queue for checked-out editions |
| `digital_resource` | `resource_id` | `title`, `resource_type`, `url`, `licence_end` | E-books, online journals, videos |
| `digital_access_log` | `log_id` | `resource_id` (FK), `member_id` (FK), `accessed_at`, `minutes_used` | Digital resource audit trail |

---

### 3. Normalization Analysis
* **1NF**: All table columns contain atomic, scalar values (no repeating groups, comma-separated lists, or arrays).
* **2NF**: All non-key attributes are fully functionally dependent on the entire primary key (composite keys in `book_author` and lookup tables have no partial dependencies).
* **3NF / BCNF**: Transitive dependencies removed. For instance, member borrowing policies (`max_books`, `loan_days`, `fine_per_day`) depend solely on `member_type`, so they are isolated in `member_policy` rather than being stored redundantly on every row in `member`.

---

## 📜 Business & Circulation Rules

### 1. Tiered Membership Borrowing Policies
Stored inside the `member_policy` table so library administrators can modify policies without code changes:

| Member Type | Max Concurrent Loans | Loan Period | Late Fine Rate |
|---|:---:|:---:|:---:|
| **Student** | 3 books | 14 days | ₹2.00 / day |
| **Faculty** | 6 books | 30 days | ₹1.00 / day |
| **Public** | 2 books | 7 days | ₹5.00 / day |

### 2. The ₹50 Fine Lock Rule
* If a member has accumulated more than **₹50.00** in unpaid fines (`balance = amount - paid_amount`), the system immediately **refuses any new book checkout**.
* The member must clear or partially pay their balance before resuming borrowing privileges.

### 3. FIFO Reservation & Hold Queue
* A member can only place a reservation on an edition if **every physical copy is currently checked out**.
* When someone places a reservation, they receive an ordered `queue_no`.
* When any issued copy of that edition is returned:
  1. The copy status changes to `ON_HOLD`.
  2. The next reservation in line (`WAITING`) transitions to `READY`.
  3. The hold copy cannot be issued to anyone other than the reservation holder.
  4. Once checked out, the reservation transitions to `FULFILLED`.

### 4. Loan Renewal Restrictions
* A book can only be renewed before its due date.
* Overdue books cannot be renewed (they must be returned and late fees settled).
* If another patron is waiting in the reservation queue for that title, **renewal is blocked**.

---

## 🖥️ Application Features & Modules

### 1. Web Application (`web_app.py`)
Accessible via any browser at `http://localhost:5000`:
* **Dashboard Overview**: Live KPI metric tiles (Active Loans, Overdue Books, Copies on Shelf, Pending Fines), an interactive Chart.js donut chart, and an overdue book action board.
* **Catalogue & Inventory**: Instant search across titles, authors, and ISBNs; filter by category; view real-time shelf availability ratios; modals to add new books or register new physical copy accession numbers.
* **Circulation Desk**:
  * **Quick Issue**: Dropdown pickers for active members and available shelf copies with immediate validation against limits and fines.
  * **Quick Return & Renew**: Automatically computes overdue days and late fines upon return; supports loan renewals.
* **Member Registry**: Comprehensive directory with member tier tags; modal drawer inspecting complete personal borrowing history and fine ledger.
* **Reservations Management**: Full visibility of patrons in line, queue rankings, and 1-click cancellations.
* **Fines Ledger**: Search unpaid fines and record payments (partial or full).
* **Digital Repository**: Interactive cards for e-books and online journals with direct access links and session duration logging.
* **Reports & Analytics**: Pre-computed operational reports (Popular Titles, Monthly Revenue Inflows, Overdue patons) with **1-click CSV Export**.
* **Zero-Setup Demo Fallback**: Works immediately out of the box with sample data, and includes a **"Connect MySQL"** modal to sync directly with local MySQL instances.

### 2. Desktop GUI (`app/app.py`)
A standalone Python Tkinter desktop program built using native `ttk` widgets:
* Styled with Segoe UI typography and a custom navy/accent palette.
* Tabbed navigation across Dashboard, Catalogue, Circulation, Members, Reservations, Fines, and Reports.

---

## 🚀 Getting Started & How to Run

### Prerequisites
* **Python**: Version 3.10 or higher.
* **MySQL**: MySQL 8.0 Server (optional for Demo Mode, required for persistent MySQL storage).

### Step 1: Install Dependencies
Open PowerShell or your terminal in the project directory:
```powershell
pip install flask mysql-connector-python
```

---

### Step 2: Run the Web Application

#### Option A: Quick Double-Click (Windows)
Double-click the provided launcher file:
* [**`run_web.bat`**](file:///c:/Users/h4v15/Downloads/hp1%20%284%29/hp1/run_web.bat)

#### Option B: Terminal Command
```powershell
python web_app.py
```

Then open your browser and go to:
👉 **[http://localhost:5000](http://localhost:5000)**

---

### Step 3: Run the Desktop GUI (Tkinter)
If you prefer running the native desktop window application:
```powershell
python app/app.py
```

---

### Step 4: Running Automated Tests
The project contains an automated test suite verifying circulation policies, transactional integrity, and fine calculations:
```powershell
python -m unittest discover -s tests -v
```

---

## 📊 Database Views Included

The database pre-compiles 6 operational SQL views in `sql/03_views.sql`:

1. **`v_available_titles`**: Lists titles with at least one available copy on the shelf, concatenating all contributing authors.
2. **`v_overdue_copies`**: Joins `issue`, `copy`, and `member` to compute days overdue and fine accrued so far.
3. **`v_member_history`**: Complete historical audit of all books borrowed by a patron, return dates, and associated fines.
4. **`v_popular_books`**: Aggregates circulation frequency by book title to identify most frequently borrowed literature.
5. **`v_reservation_queue`**: Uses SQL Window Functions (`ROW_NUMBER() OVER (...)`) to compute exact queue positions for waiting patrons.
6. **`v_fine_summary`**: Aggregates fine amounts levied, collected, and pending grouped by calendar month.

---

## 📂 Project Directory Structure

```
hp1/
├── app/
│   ├── app.py                     # Desktop GUI frontend (Python Tkinter)
│   └── library.py                 # Core database business rules engine & transactions
├── sql/
│   ├── 01_schema.sql              # MySQL DDL (Table definitions, constraints, relations)
│   ├── 02_sample_data.sql         # Seed dataset (Books, authors, members, active loans)
│   ├── 03_views.sql               # Pre-compiled analytical SQL views
│   └── 04_queries.sql             # Benchmark evaluation queries (Joins, Aggregates, Subqueries)
├── tests/
│   └── test_library.py            # Automated integration and edge-case unit tests
├── templates/
│   └── index.html                 # Modern Tailwind CSS / Chart.js Web Interface
├── docs/
│   ├── report.md                  # Academic specification report
│   ├── Jai_Havish_Sannapareddy_DBMS_PBL_Report.docx  # Formatted Word submission
│   └── Jai_Havish_Sannapareddy_DBMS_PBL_Report.pdf   # Formatted PDF report
├── web_app.py                     # Web server backend (Flask REST API + MySQL connector)
├── run_web.bat                    # 1-click Windows launcher for web application
└── README.md                      # Comprehensive project documentation (this file)
```

---

## 👨‍💻 Project Information
* **Project Title**: Library Circulation and Digital Resource Management System
* **Course / Subject**: Database Management Systems (DBMS PBL Project 02)
* **Author**: Jai Havish Sannapareddy
* **Roll No**: 25WU0102103
* **Program / Section**: AI/ML / AI/ML RHINOS
* **Faculty**: Miss Sahiti
* **Submission Date**: 15/10/2026
* **Database Engine**: MySQL 8.0 (InnoDB)
* **Programming Language**: Python 3
