-- Library Circulation and Digital Resource Management System
-- MySQL 8.0.16 or newer (CHECK constraints are enforced from this version)

DROP DATABASE IF EXISTS library_db;
CREATE DATABASE library_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE library_db;

-- ---------- lookup tables ----------

CREATE TABLE publisher (
    publisher_id INT AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(100) NOT NULL UNIQUE,
    city         VARCHAR(60)
);

CREATE TABLE author (
    author_id INT AUTO_INCREMENT PRIMARY KEY,
    name      VARCHAR(100) NOT NULL,
    country   VARCHAR(60)
);

CREATE TABLE category (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(60) NOT NULL UNIQUE
);

-- Loan rules depend only on the member type, so they live in their own table
CREATE TABLE member_policy (
    member_type  VARCHAR(10) PRIMARY KEY,
    max_books    TINYINT       NOT NULL CHECK (max_books > 0),
    loan_days    TINYINT       NOT NULL CHECK (loan_days > 0),
    fine_per_day DECIMAL(5,2)  NOT NULL DEFAULT 2.00 CHECK (fine_per_day >= 0)
);

CREATE TABLE staff (
    staff_id  INT AUTO_INCREMENT PRIMARY KEY,
    username  VARCHAR(30) NOT NULL UNIQUE,
    full_name VARCHAR(80) NOT NULL,
    role      ENUM('LIBRARIAN','ADMIN') NOT NULL DEFAULT 'LIBRARIAN'
);

-- ---------- catalogue ----------

-- one row per title (the work itself)
CREATE TABLE book (
    book_id     INT AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    category_id INT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES category(category_id)
);

CREATE TABLE book_author (
    book_id   INT NOT NULL,
    author_id INT NOT NULL,
    PRIMARY KEY (book_id, author_id),
    FOREIGN KEY (book_id)   REFERENCES book(book_id)     ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES author(author_id)
);

-- one row per printed edition of a title
CREATE TABLE edition (
    edition_id   INT AUTO_INCREMENT PRIMARY KEY,
    book_id      INT NOT NULL,
    publisher_id INT NOT NULL,
    isbn         CHAR(13) NOT NULL UNIQUE,
    edition_no   TINYINT  NOT NULL DEFAULT 1 CHECK (edition_no > 0),
    pub_year     SMALLINT NOT NULL CHECK (pub_year BETWEEN 1450 AND 2100),
    pages        SMALLINT CHECK (pages > 0),
    UNIQUE (book_id, publisher_id, edition_no),
    FOREIGN KEY (book_id)      REFERENCES book(book_id),
    FOREIGN KEY (publisher_id) REFERENCES publisher(publisher_id),
    CHECK (isbn REGEXP '^[0-9]{13}$')
);

-- one row per physical copy on the shelf
CREATE TABLE copy (
    copy_id      INT AUTO_INCREMENT PRIMARY KEY,
    edition_id   INT NOT NULL,
    accession_no VARCHAR(15) NOT NULL UNIQUE,
    shelf        VARCHAR(20),
    status       ENUM('AVAILABLE','ISSUED','ON_HOLD','LOST','WITHDRAWN')
                 NOT NULL DEFAULT 'AVAILABLE',
    added_on     DATE NOT NULL DEFAULT (CURRENT_DATE),
    FOREIGN KEY (edition_id) REFERENCES edition(edition_id)
);

-- ---------- members ----------

CREATE TABLE member (
    member_id   INT AUTO_INCREMENT PRIMARY KEY,
    card_no     VARCHAR(12) NOT NULL UNIQUE,
    full_name   VARCHAR(100) NOT NULL,
    email       VARCHAR(120) NOT NULL UNIQUE,
    phone       VARCHAR(15),
    member_type VARCHAR(10) NOT NULL DEFAULT 'STUDENT',
    joined_on   DATE NOT NULL DEFAULT (CURRENT_DATE),
    expiry_date DATE NOT NULL,
    status      ENUM('ACTIVE','SUSPENDED','EXPIRED') NOT NULL DEFAULT 'ACTIVE',
    FOREIGN KEY (member_type) REFERENCES member_policy(member_type),
    CHECK (expiry_date > joined_on),
    CHECK (email LIKE '%_@_%._%')
);

-- ---------- circulation ----------

CREATE TABLE issue (
    issue_id    INT AUTO_INCREMENT PRIMARY KEY,
    copy_id     INT  NOT NULL,
    member_id   INT  NOT NULL,
    issued_by   INT,
    issue_date  DATE NOT NULL,
    due_date    DATE NOT NULL,
    return_date DATE NULL,
    -- holds the copy id only while the book is out, NULL after return.
    -- A UNIQUE index on it gives "one active issue per copy".
    active_copy_id INT GENERATED ALWAYS AS (IF(return_date IS NULL, copy_id, NULL)) STORED,
    UNIQUE (active_copy_id),
    FOREIGN KEY (copy_id)   REFERENCES copy(copy_id),
    FOREIGN KEY (member_id) REFERENCES member(member_id),
    FOREIGN KEY (issued_by) REFERENCES staff(staff_id),
    CHECK (due_date > issue_date),
    CHECK (return_date IS NULL OR return_date >= issue_date)
);

CREATE TABLE reservation (
    reservation_id INT AUTO_INCREMENT PRIMARY KEY,
    edition_id     INT NOT NULL,
    member_id      INT NOT NULL,
    queue_no       INT NOT NULL CHECK (queue_no > 0),
    reserved_on    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status         ENUM('WAITING','READY','FULFILLED','CANCELLED','EXPIRED')
                   NOT NULL DEFAULT 'WAITING',
    copy_id        INT NULL,          -- copy kept aside once status is READY
    ready_on       DATE NULL,
    -- these two stay filled only for live reservations
    live_queue_no  INT GENERATED ALWAYS AS
                   (IF(status IN ('WAITING','READY'), queue_no, NULL)) STORED,
    live_member_id INT GENERATED ALWAYS AS
                   (IF(status IN ('WAITING','READY'), member_id, NULL)) STORED,
    UNIQUE (edition_id, live_queue_no),    -- no two people share a queue number
    UNIQUE (edition_id, live_member_id),   -- one live reservation per member per edition
    FOREIGN KEY (edition_id) REFERENCES edition(edition_id),
    FOREIGN KEY (member_id)  REFERENCES member(member_id),
    FOREIGN KEY (copy_id)    REFERENCES copy(copy_id),
    CHECK (status <> 'READY' OR copy_id IS NOT NULL)
);

CREATE TABLE fine (
    fine_id     INT AUTO_INCREMENT PRIMARY KEY,
    issue_id    INT NOT NULL UNIQUE,
    days_late   SMALLINT     NOT NULL CHECK (days_late >= 0),
    amount      DECIMAL(8,2) NOT NULL DEFAULT 0 CHECK (amount >= 0),
    paid_amount DECIMAL(8,2) NOT NULL DEFAULT 0 CHECK (paid_amount >= 0),
    assessed_on DATE NOT NULL DEFAULT (CURRENT_DATE),
    paid_on     DATE NULL,
    FOREIGN KEY (issue_id) REFERENCES issue(issue_id),
    CHECK (paid_amount <= amount)
);

-- ---------- digital resources ----------

CREATE TABLE digital_resource (
    resource_id   INT AUTO_INCREMENT PRIMARY KEY,
    title         VARCHAR(200) NOT NULL,
    resource_type ENUM('EBOOK','JOURNAL','VIDEO','DATABASE') NOT NULL,
    publisher_id  INT,
    url           VARCHAR(255) NOT NULL,
    licence_end   DATE,
    FOREIGN KEY (publisher_id) REFERENCES publisher(publisher_id)
);

CREATE TABLE digital_access_log (
    log_id       INT AUTO_INCREMENT PRIMARY KEY,
    resource_id  INT NOT NULL,
    member_id    INT NOT NULL,
    accessed_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    minutes_used SMALLINT NOT NULL DEFAULT 0 CHECK (minutes_used >= 0),
    FOREIGN KEY (resource_id) REFERENCES digital_resource(resource_id),
    FOREIGN KEY (member_id)   REFERENCES member(member_id)
);

-- ---------- indexes for frequent searches ----------
-- (PRIMARY KEY, UNIQUE and FOREIGN KEY columns already get an index)

CREATE INDEX idx_book_title      ON book(title);
CREATE INDEX idx_author_name     ON author(name);
CREATE INDEX idx_member_name     ON member(full_name);
CREATE INDEX idx_copy_ed_status  ON copy(edition_id, status);
CREATE INDEX idx_issue_due       ON issue(due_date, return_date);
CREATE INDEX idx_issue_member    ON issue(member_id, issue_date);
CREATE INDEX idx_res_status      ON reservation(edition_id, status);
CREATE INDEX idx_log_res_time    ON digital_access_log(resource_id, accessed_at);
