USE library_db;

-- Titles with at least one copy on the shelf right now
CREATE OR REPLACE VIEW v_available_titles AS
SELECT e.edition_id, b.title, e.isbn, e.edition_no, c.name AS category,
       GROUP_CONCAT(DISTINCT a.name ORDER BY a.name SEPARATOR ', ') AS authors,
       COUNT(DISTINCT cp.copy_id) AS copies_available
FROM edition e
JOIN book b          ON b.book_id = e.book_id
JOIN category c      ON c.category_id = b.category_id
JOIN book_author ba  ON ba.book_id = b.book_id
JOIN author a        ON a.author_id = ba.author_id
JOIN copy cp         ON cp.edition_id = e.edition_id AND cp.status = 'AVAILABLE'
GROUP BY e.edition_id, b.title, e.isbn, e.edition_no, c.name;

-- Copies that are past their due date and not yet back
CREATE OR REPLACE VIEW v_overdue_copies AS
SELECT i.issue_id, cp.accession_no, b.title, m.card_no, m.full_name, m.email,
       i.issue_date, i.due_date,
       DATEDIFF(CURDATE(), i.due_date)                    AS days_overdue,
       DATEDIFF(CURDATE(), i.due_date) * mp.fine_per_day  AS fine_so_far
FROM issue i
JOIN copy cp          ON cp.copy_id = i.copy_id
JOIN edition e        ON e.edition_id = cp.edition_id
JOIN book b           ON b.book_id = e.book_id
JOIN member m         ON m.member_id = i.member_id
JOIN member_policy mp ON mp.member_type = m.member_type
WHERE i.return_date IS NULL AND i.due_date < CURDATE();

-- Everything a member has borrowed, with the fine if there was one
CREATE OR REPLACE VIEW v_member_history AS
SELECT m.member_id, m.card_no, m.full_name, b.title, cp.accession_no,
       i.issue_date, i.due_date, i.return_date,
       CASE WHEN i.return_date IS NULL AND i.due_date < CURDATE() THEN 'OVERDUE'
            WHEN i.return_date IS NULL THEN 'ON LOAN'
            ELSE 'RETURNED' END AS loan_status,
       COALESCE(f.amount, 0) AS fine_amount
FROM issue i
JOIN member m   ON m.member_id = i.member_id
JOIN copy cp    ON cp.copy_id = i.copy_id
JOIN edition e  ON e.edition_id = cp.edition_id
JOIN book b     ON b.book_id = e.book_id
LEFT JOIN fine f ON f.issue_id = i.issue_id;

-- Number of times each title has been issued
CREATE OR REPLACE VIEW v_popular_books AS
SELECT b.book_id, b.title, COUNT(i.issue_id) AS times_issued
FROM book b
JOIN edition e ON e.book_id = b.book_id
JOIN copy cp   ON cp.edition_id = e.edition_id
JOIN issue i   ON i.copy_id = cp.copy_id
GROUP BY b.book_id, b.title;

-- Waiting list, in queue order
CREATE OR REPLACE VIEW v_reservation_queue AS
SELECT r.reservation_id, b.title, e.edition_id, r.queue_no, m.full_name,
       r.status, r.reserved_on,
       ROW_NUMBER() OVER (PARTITION BY r.edition_id ORDER BY r.queue_no) AS position_in_line
FROM reservation r
JOIN edition e ON e.edition_id = r.edition_id
JOIN book b    ON b.book_id = e.book_id
JOIN member m  ON m.member_id = r.member_id
WHERE r.status IN ('WAITING','READY');

-- Fine money per month
CREATE OR REPLACE VIEW v_fine_summary AS
SELECT DATE_FORMAT(assessed_on, '%Y-%m') AS month,
       COUNT(*)                          AS fines_raised,
       SUM(amount)                       AS total_fined,
       SUM(paid_amount)                  AS total_collected,
       SUM(amount - paid_amount)         AS still_pending
FROM fine
GROUP BY DATE_FORMAT(assessed_on, '%Y-%m');
