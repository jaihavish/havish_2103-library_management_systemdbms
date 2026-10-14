USE library_db;

-- Q1. Simple retrieval: all active members, sorted by name
SELECT card_no, full_name, member_type, expiry_date
FROM member WHERE status = 'ACTIVE' ORDER BY full_name;

-- Q2. Join: every title with its authors, publisher and year
SELECT b.title, GROUP_CONCAT(a.name SEPARATOR ', ') AS authors,
       p.name AS publisher, e.pub_year, e.isbn
FROM book b
JOIN edition e      ON e.book_id = b.book_id
JOIN publisher p    ON p.publisher_id = e.publisher_id
JOIN book_author ba ON ba.book_id = b.book_id
JOIN author a       ON a.author_id = ba.author_id
GROUP BY e.edition_id, b.title, p.name, e.pub_year, e.isbn
ORDER BY b.title;

-- Q3. Search by title or author (what the front end runs)
SELECT DISTINCT b.title, e.isbn
FROM book b
JOIN edition e      ON e.book_id = b.book_id
JOIN book_author ba ON ba.book_id = b.book_id
JOIN author a       ON a.author_id = ba.author_id
WHERE b.title LIKE '%data%' OR a.name LIKE '%Silberschatz%';

-- Q4. Available titles (view)
SELECT title, edition_no, authors, copies_available
FROM v_available_titles ORDER BY title;

-- Q5. Overdue copies with fine so far (view)
SELECT accession_no, title, full_name, due_date, days_overdue, fine_so_far
FROM v_overdue_copies ORDER BY days_overdue DESC;

-- Q6. Member history for one member (view)
SELECT title, issue_date, due_date, return_date, loan_status, fine_amount
FROM v_member_history WHERE card_no = 'LIB2025001' ORDER BY issue_date DESC;

-- Q7. Aggregate: five most popular books
SELECT title, times_issued FROM v_popular_books
ORDER BY times_issued DESC, title LIMIT 5;

-- Q8. Aggregate with GROUP BY and HAVING: members who borrowed 3 or more books
SELECT m.full_name, COUNT(*) AS books_borrowed
FROM issue i JOIN member m ON m.member_id = i.member_id
GROUP BY m.member_id, m.full_name
HAVING COUNT(*) >= 3
ORDER BY books_borrowed DESC;

-- Q9. Books per category with copy counts
SELECT c.name AS category, COUNT(DISTINCT b.book_id) AS titles, COUNT(cp.copy_id) AS copies
FROM category c
LEFT JOIN book b    ON b.category_id = c.category_id
LEFT JOIN edition e ON e.book_id = b.book_id
LEFT JOIN copy cp   ON cp.edition_id = e.edition_id
GROUP BY c.category_id, c.name ORDER BY copies DESC;

-- Q10. Nested query: books that have never been issued
SELECT title FROM book
WHERE book_id NOT IN (SELECT e.book_id FROM edition e
                      JOIN copy cp ON cp.edition_id = e.edition_id
                      JOIN issue i ON i.copy_id = cp.copy_id);

-- Q11. Nested query: members who owe more than the average unpaid fine
SELECT m.full_name, SUM(f.amount - f.paid_amount) AS owed
FROM fine f
JOIN issue i  ON i.issue_id = f.issue_id
JOIN member m ON m.member_id = i.member_id
GROUP BY m.member_id, m.full_name
HAVING SUM(f.amount - f.paid_amount) >
       (SELECT AVG(amount - paid_amount) FROM fine WHERE amount > paid_amount);

-- Q12. Correlated subquery: members currently holding more than one book
SELECT m.full_name,
       (SELECT COUNT(*) FROM issue i
        WHERE i.member_id = m.member_id AND i.return_date IS NULL) AS books_out
FROM member m
WHERE (SELECT COUNT(*) FROM issue i
       WHERE i.member_id = m.member_id AND i.return_date IS NULL) > 1;

-- Q13. Reservation queue (view)
SELECT title, position_in_line, full_name, status, reserved_on
FROM v_reservation_queue ORDER BY title, position_in_line;

-- Q14. Fine collection per month (view)
SELECT * FROM v_fine_summary ORDER BY month;

-- Q15. Unpaid fines per member
SELECT m.card_no, m.full_name, SUM(f.amount - f.paid_amount) AS unpaid
FROM fine f
JOIN issue i  ON i.issue_id = f.issue_id
JOIN member m ON m.member_id = i.member_id
WHERE f.amount > f.paid_amount
GROUP BY m.member_id, m.card_no, m.full_name;

-- Q16. Digital access: uses and minutes per resource
SELECT d.title, d.resource_type, COUNT(l.log_id) AS visits,
       COALESCE(SUM(l.minutes_used), 0) AS total_minutes
FROM digital_resource d
LEFT JOIN digital_access_log l ON l.resource_id = d.resource_id
GROUP BY d.resource_id, d.title, d.resource_type
ORDER BY visits DESC;

-- Q17. Digital resources whose licence has already ended
SELECT title, licence_end FROM digital_resource WHERE licence_end < CURDATE();

-- Q18. Copies status summary
SELECT status, COUNT(*) AS copies FROM copy GROUP BY status;

-- Q19. Average days a book is kept (returned loans only)
SELECT ROUND(AVG(DATEDIFF(return_date, issue_date)), 1) AS avg_days_kept
FROM issue WHERE return_date IS NOT NULL;

-- Q20. Check the index is used for a title search
EXPLAIN SELECT * FROM book WHERE title LIKE 'Data%';
