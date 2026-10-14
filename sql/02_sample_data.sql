-- Sample data. Dates are written relative to today so that the
-- overdue and fine reports still show something whenever the script is run.
USE library_db;

INSERT INTO member_policy (member_type, max_books, loan_days, fine_per_day) VALUES
('STUDENT', 3, 14, 2.00),
('FACULTY', 6, 30, 1.00),
('PUBLIC',  2,  7, 5.00);

INSERT INTO staff (username, full_name, role) VALUES
('meera', 'Meera Nair',   'LIBRARIAN'),
('arjun', 'Arjun Mehta',  'LIBRARIAN'),
('admin', 'Library Admin','ADMIN');

INSERT INTO publisher (name, city) VALUES
('Pearson Education',        'Noida'),
('McGraw Hill',              'New York'),
('Oxford University Press',  'Oxford'),
('Penguin Books',            'London'),
('O''Reilly Media',          'Sebastopol'),
('MIT Press',                'Cambridge');

INSERT INTO category (name) VALUES
('Computer Science'), ('Fiction'), ('History'),
('Science'), ('Management'), ('Mathematics');

INSERT INTO author (name, country) VALUES
('Abraham Silberschatz', 'USA'),      -- 1
('Henry Korth',          'USA'),      -- 2
('S. Sudarshan',         'India'),    -- 3
('Ramez Elmasri',        'USA'),      -- 4
('Shamkant Navathe',     'USA'),      -- 5
('Thomas Cormen',        'USA'),      -- 6
('Mark Lutz',            'USA'),      -- 7
('Robert C. Martin',     'USA'),      -- 8
('R. K. Narayan',        'India'),    -- 9
('Khushwant Singh',      'India'),    -- 10
('Stephen Hawking',      'UK'),       -- 11
('Ramachandra Guha',     'India'),    -- 12
('Harold Koontz',        'USA'),      -- 13
('B. S. Grewal',         'India'),    -- 14
('A. P. J. Abdul Kalam', 'India'),    -- 15
('Peter Galvin',         'USA'),      -- 16
('Kenneth Rosen',        'USA'),      -- 17
('Andrew Tanenbaum',     'Netherlands'); -- 18

INSERT INTO book (title, category_id) VALUES
('Database System Concepts',          1),  -- 1
('Fundamentals of Database Systems',  1),  -- 2
('Introduction to Algorithms',        1),  -- 3
('Learning Python',                   1),  -- 4
('Clean Code',                        1),  -- 5
('The Guide',                         2),  -- 6
('Train to Pakistan',                 2),  -- 7
('A Brief History of Time',           4),  -- 8
('India After Gandhi',                3),  -- 9
('Principles of Management',          5),  -- 10
('Higher Engineering Mathematics',    6),  -- 11
('Wings of Fire',                     3),  -- 12
('Operating System Concepts',         1),  -- 13
('Discrete Mathematics',              6),  -- 14
('Computer Networks',                 1);  -- 15

INSERT INTO book_author (book_id, author_id) VALUES
(1,1),(1,2),(1,3),(2,4),(2,5),(3,6),(4,7),(5,8),(6,9),(7,10),
(8,11),(9,12),(10,13),(11,14),(12,15),(13,1),(13,16),(14,17),(15,18);

INSERT INTO edition (book_id, publisher_id, isbn, edition_no, pub_year, pages) VALUES
(1,  2, '9780078022159', 6, 2010, 1376),   -- e1
(1,  2, '9781260084504', 7, 2019, 1344),   -- e2
(2,  1, '9780133970777', 7, 2015, 1272),   -- e3
(3,  6, '9780262033848', 3, 2009, 1292),   -- e4
(4,  5, '9781449355739', 5, 2013, 1648),   -- e5
(5,  1, '9780132350884', 1, 2008,  464),   -- e6
(6,  4, '9780143039655', 1, 2006,  224),   -- e7
(7,  4, '9780143065883', 1, 2009,  192),   -- e8
(8,  4, '9780553380163', 1, 1998,  212),   -- e9
(9,  3, '9780330540209', 1, 2008,  900),   -- e10
(10, 2, '9780070347588', 1, 2004,  640),   -- e11
(11, 2, '9780070608788', 1, 2010, 1200),   -- e12
(12, 4, '9788173711466', 1, 1999,  180),   -- e13
(13, 1, '9781118063330', 9, 2012,  976),   -- e14
(14, 2, '9780073383095', 7, 2011, 1072),   -- e15
(15, 1, '9780132126953', 5, 2010,  960);   -- e16

-- 36 copies: ids 1-3 e1, 4-5 e2, 6-8 e3, 9-10 e4, 11-12 e5, 13-15 e6, 16-17 e7,
-- 18-19 e8, 20-21 e9, 22-23 e10, 24-25 e11, 26-28 e12, 29-30 e13, 31-32 e14,
-- 33-34 e15, 35-36 e16. Status values match the issues and holds loaded below.
INSERT INTO copy (edition_id, accession_no, shelf, status) VALUES
(1,'ACC-0001','CS-A1','ISSUED'),   (1,'ACC-0002','CS-A1','AVAILABLE'), (1,'ACC-0003','CS-A1','AVAILABLE'),
(2,'ACC-0004','CS-A1','AVAILABLE'),(2,'ACC-0005','CS-A1','AVAILABLE'),
(3,'ACC-0006','CS-A2','ISSUED'),   (3,'ACC-0007','CS-A2','AVAILABLE'), (3,'ACC-0008','CS-A2','AVAILABLE'),
(4,'ACC-0009','CS-A3','AVAILABLE'),(4,'ACC-0010','CS-A3','ISSUED'),
(5,'ACC-0011','CS-B1','AVAILABLE'),(5,'ACC-0012','CS-B1','AVAILABLE'),
(6,'ACC-0013','CS-B2','ISSUED'),   (6,'ACC-0014','CS-B2','ISSUED'),   (6,'ACC-0015','CS-B2','AVAILABLE'),
(7,'ACC-0016','FI-C1','ISSUED'),   (7,'ACC-0017','FI-C1','AVAILABLE'),
(8,'ACC-0018','FI-C1','AVAILABLE'),(8,'ACC-0019','FI-C1','AVAILABLE'),
(9,'ACC-0020','SC-D1','ISSUED'),   (9,'ACC-0021','SC-D1','AVAILABLE'),
(10,'ACC-0022','HI-E1','AVAILABLE'),(10,'ACC-0023','HI-E1','AVAILABLE'),
(11,'ACC-0024','MG-F1','AVAILABLE'),(11,'ACC-0025','MG-F1','AVAILABLE'),
(12,'ACC-0026','MA-G1','AVAILABLE'),(12,'ACC-0027','MA-G1','AVAILABLE'),(12,'ACC-0028','MA-G1','ISSUED'),
(13,'ACC-0029','HI-E2','ON_HOLD'), (13,'ACC-0030','HI-E2','ISSUED'),
(14,'ACC-0031','CS-C1','AVAILABLE'),(14,'ACC-0032','CS-C1','AVAILABLE'),
(15,'ACC-0033','MA-G2','AVAILABLE'),(15,'ACC-0034','MA-G2','AVAILABLE'),
(16,'ACC-0035','CS-C2','AVAILABLE'),(16,'ACC-0036','CS-C2','ISSUED');

INSERT INTO member (card_no, full_name, email, phone, member_type, joined_on, expiry_date, status) VALUES
('LIB2025001','Aarav Sharma',   'aarav.sharma@college.edu',  '9810011001','STUDENT', DATE_SUB(CURDATE(), INTERVAL 400 DAY), DATE_ADD(CURDATE(), INTERVAL 300 DAY),'ACTIVE'),
('LIB2025002','Diya Patel',     'diya.patel@college.edu',    '9810011002','STUDENT', DATE_SUB(CURDATE(), INTERVAL 400 DAY), DATE_ADD(CURDATE(), INTERVAL 300 DAY),'ACTIVE'),
('LIB2025003','Rohan Gupta',    'rohan.gupta@college.edu',   '9810011003','STUDENT', DATE_SUB(CURDATE(), INTERVAL 390 DAY), DATE_ADD(CURDATE(), INTERVAL 310 DAY),'ACTIVE'),
('LIB2025004','Ananya Iyer',    'ananya.iyer@college.edu',   '9810011004','STUDENT', DATE_SUB(CURDATE(), INTERVAL 380 DAY), DATE_ADD(CURDATE(), INTERVAL 320 DAY),'ACTIVE'),
('LIB2025005','Karan Verma',    'karan.verma@college.edu',   '9810011005','STUDENT', DATE_SUB(CURDATE(), INTERVAL 370 DAY), DATE_ADD(CURDATE(), INTERVAL 330 DAY),'ACTIVE'),
('LIB2025006','Sneha Reddy',    'sneha.reddy@college.edu',   '9810011006','STUDENT', DATE_SUB(CURDATE(), INTERVAL 360 DAY), DATE_ADD(CURDATE(), INTERVAL 340 DAY),'ACTIVE'),
('LIB2025007','Vikram Singh',   'vikram.singh@college.edu',  '9810011007','STUDENT', DATE_SUB(CURDATE(), INTERVAL 350 DAY), DATE_ADD(CURDATE(), INTERVAL 350 DAY),'ACTIVE'),
('LIB2024101','Dr. Neha Kapoor','neha.kapoor@college.edu',   '9810022001','FACULTY', DATE_SUB(CURDATE(), INTERVAL 900 DAY), DATE_ADD(CURDATE(), INTERVAL 800 DAY),'ACTIVE'),
('LIB2024102','Prof. R. Menon', 'r.menon@college.edu',       '9810022002','FACULTY', DATE_SUB(CURDATE(), INTERVAL 900 DAY), DATE_ADD(CURDATE(), INTERVAL 800 DAY),'ACTIVE'),
('LIB2025201','Manoj Kulkarni', 'manoj.k@mail.com',          '9810033001','PUBLIC',  DATE_SUB(CURDATE(), INTERVAL 200 DAY), DATE_ADD(CURDATE(), INTERVAL 165 DAY),'ACTIVE'),
('LIB2025202','Fatima Khan',    'fatima.khan@mail.com',      '9810033002','PUBLIC',  DATE_SUB(CURDATE(), INTERVAL 150 DAY), DATE_ADD(CURDATE(), INTERVAL 215 DAY),'ACTIVE'),
('LIB2023015','Ishaan Joshi',   'ishaan.joshi@college.edu',  '9810011012','STUDENT', DATE_SUB(CURDATE(), INTERVAL 800 DAY), DATE_SUB(CURDATE(), INTERVAL 30 DAY), 'EXPIRED');

-- ---------- past circulation (all returned) ----------
-- columns: copy, member, staff, issue_date, due_date, return_date
INSERT INTO issue (copy_id, member_id, issued_by, issue_date, due_date, return_date) VALUES
( 1, 1, 1, DATE_SUB(CURDATE(), INTERVAL 120 DAY), DATE_SUB(CURDATE(), INTERVAL 106 DAY), DATE_SUB(CURDATE(), INTERVAL 108 DAY)), -- 1
( 2, 2, 1, DATE_SUB(CURDATE(), INTERVAL 110 DAY), DATE_SUB(CURDATE(), INTERVAL  96 DAY), DATE_SUB(CURDATE(), INTERVAL  90 DAY)), -- 2 late 6
( 6, 3, 2, DATE_SUB(CURDATE(), INTERVAL 100 DAY), DATE_SUB(CURDATE(), INTERVAL  86 DAY), DATE_SUB(CURDATE(), INTERVAL  90 DAY)), -- 3
( 9, 1, 1, DATE_SUB(CURDATE(), INTERVAL  95 DAY), DATE_SUB(CURDATE(), INTERVAL  81 DAY), DATE_SUB(CURDATE(), INTERVAL  78 DAY)), -- 4 late 3
(11, 4, 2, DATE_SUB(CURDATE(), INTERVAL  90 DAY), DATE_SUB(CURDATE(), INTERVAL  76 DAY), DATE_SUB(CURDATE(), INTERVAL  76 DAY)), -- 5
(13, 5, 1, DATE_SUB(CURDATE(), INTERVAL  85 DAY), DATE_SUB(CURDATE(), INTERVAL  71 DAY), DATE_SUB(CURDATE(), INTERVAL  60 DAY)), -- 6 late 11
(16, 6, 2, DATE_SUB(CURDATE(), INTERVAL  80 DAY), DATE_SUB(CURDATE(), INTERVAL  66 DAY), DATE_SUB(CURDATE(), INTERVAL  71 DAY)), -- 7
(18, 7, 1, DATE_SUB(CURDATE(), INTERVAL  75 DAY), DATE_SUB(CURDATE(), INTERVAL  61 DAY), DATE_SUB(CURDATE(), INTERVAL  60 DAY)), -- 8 late 1
(20, 2, 2, DATE_SUB(CURDATE(), INTERVAL  70 DAY), DATE_SUB(CURDATE(), INTERVAL  56 DAY), DATE_SUB(CURDATE(), INTERVAL  57 DAY)), -- 9
(26, 8, 1, DATE_SUB(CURDATE(), INTERVAL  66 DAY), DATE_SUB(CURDATE(), INTERVAL  36 DAY), DATE_SUB(CURDATE(), INTERVAL  38 DAY)), -- 10
(27, 9, 1, DATE_SUB(CURDATE(), INTERVAL  60 DAY), DATE_SUB(CURDATE(), INTERVAL  30 DAY), DATE_SUB(CURDATE(), INTERVAL  20 DAY)), -- 11 late 10
(29,10, 2, DATE_SUB(CURDATE(), INTERVAL  55 DAY), DATE_SUB(CURDATE(), INTERVAL  48 DAY), DATE_SUB(CURDATE(), INTERVAL  43 DAY)), -- 12 late 5
(31,11, 2, DATE_SUB(CURDATE(), INTERVAL  50 DAY), DATE_SUB(CURDATE(), INTERVAL  43 DAY), DATE_SUB(CURDATE(), INTERVAL  43 DAY)), -- 13
( 3, 3, 1, DATE_SUB(CURDATE(), INTERVAL  45 DAY), DATE_SUB(CURDATE(), INTERVAL  31 DAY), DATE_SUB(CURDATE(), INTERVAL  31 DAY)), -- 14
( 6, 1, 1, DATE_SUB(CURDATE(), INTERVAL  40 DAY), DATE_SUB(CURDATE(), INTERVAL  26 DAY), DATE_SUB(CURDATE(), INTERVAL  29 DAY)), -- 15
( 1, 4, 2, DATE_SUB(CURDATE(), INTERVAL  35 DAY), DATE_SUB(CURDATE(), INTERVAL  21 DAY), DATE_SUB(CURDATE(), INTERVAL  22 DAY)), -- 16
(13, 2, 2, DATE_SUB(CURDATE(), INTERVAL  30 DAY), DATE_SUB(CURDATE(), INTERVAL  16 DAY), DATE_SUB(CURDATE(), INTERVAL  16 DAY)), -- 17
(33, 5, 1, DATE_SUB(CURDATE(), INTERVAL  28 DAY), DATE_SUB(CURDATE(), INTERVAL  14 DAY), DATE_SUB(CURDATE(), INTERVAL   8 DAY)), -- 18 late 6
(35, 6, 2, DATE_SUB(CURDATE(), INTERVAL  25 DAY), DATE_SUB(CURDATE(), INTERVAL  11 DAY), DATE_SUB(CURDATE(), INTERVAL  15 DAY)), -- 19
(22, 7, 1, DATE_SUB(CURDATE(), INTERVAL  24 DAY), DATE_SUB(CURDATE(), INTERVAL  10 DAY), DATE_SUB(CURDATE(), INTERVAL  10 DAY)), -- 20
(26, 3, 1, DATE_SUB(CURDATE(), INTERVAL  22 DAY), DATE_SUB(CURDATE(), INTERVAL   8 DAY), DATE_SUB(CURDATE(), INTERVAL  10 DAY)), -- 21
( 4, 1, 2, DATE_SUB(CURDATE(), INTERVAL  20 DAY), DATE_SUB(CURDATE(), INTERVAL   6 DAY), DATE_SUB(CURDATE(), INTERVAL  11 DAY)), -- 22
( 9, 2, 2, DATE_SUB(CURDATE(), INTERVAL  18 DAY), DATE_SUB(CURDATE(), INTERVAL   4 DAY), DATE_SUB(CURDATE(), INTERVAL  10 DAY)), -- 23
(24, 4, 1, DATE_SUB(CURDATE(), INTERVAL  16 DAY), DATE_SUB(CURDATE(), INTERVAL   2 DAY), DATE_SUB(CURDATE(), INTERVAL   6 DAY)); -- 24

-- ---------- books that are out right now ----------
INSERT INTO issue (copy_id, member_id, issued_by, issue_date, due_date) VALUES
( 1, 1, 1, DATE_SUB(CURDATE(), INTERVAL 20 DAY), DATE_SUB(CURDATE(), INTERVAL  6 DAY)), -- 25 overdue
( 6, 1, 1, DATE_SUB(CURDATE(), INTERVAL 10 DAY), DATE_ADD(CURDATE(), INTERVAL  4 DAY)), -- 26
(10, 3, 2, DATE_SUB(CURDATE(), INTERVAL 25 DAY), DATE_SUB(CURDATE(), INTERVAL 11 DAY)), -- 27 overdue
(13, 5, 1, DATE_SUB(CURDATE(), INTERVAL 15 DAY), DATE_SUB(CURDATE(), INTERVAL  1 DAY)), -- 28 overdue
(28, 8, 1, DATE_SUB(CURDATE(), INTERVAL 40 DAY), DATE_SUB(CURDATE(), INTERVAL 10 DAY)), -- 29 overdue (faculty)
(20, 9, 2, DATE_SUB(CURDATE(), INTERVAL  5 DAY), DATE_ADD(CURDATE(), INTERVAL 25 DAY)), -- 30
(30,10, 2, DATE_SUB(CURDATE(), INTERVAL  9 DAY), DATE_SUB(CURDATE(), INTERVAL  2 DAY)), -- 31 overdue (public)
(36, 6, 1, DATE_SUB(CURDATE(), INTERVAL 12 DAY), DATE_ADD(CURDATE(), INTERVAL  2 DAY)), -- 32
(14, 2, 2, DATE_SUB(CURDATE(), INTERVAL  6 DAY), DATE_ADD(CURDATE(), INTERVAL  8 DAY)), -- 33
(16, 6, 1, DATE_SUB(CURDATE(), INTERVAL  3 DAY), DATE_ADD(CURDATE(), INTERVAL 11 DAY)); -- 34

-- ---------- fines for late returns ----------
INSERT INTO fine (issue_id, days_late, amount, paid_amount, assessed_on, paid_on)
SELECT i.issue_id, v.d, v.a, v.p, i.return_date,
       IF(v.p > 0, DATE_ADD(i.return_date, INTERVAL 2 DAY), NULL)
FROM issue i
JOIN (SELECT  2 id,  6 d, 12.00 a, 12.00 p UNION ALL
      SELECT  4,  3,  6.00,  6.00 UNION ALL
      SELECT  6, 11, 22.00, 22.00 UNION ALL
      SELECT  8,  1,  2.00,  2.00 UNION ALL
      SELECT 11, 10, 10.00,  5.00 UNION ALL
      SELECT 12,  5, 25.00,  0.00 UNION ALL
      SELECT 18,  6, 12.00,  0.00) v ON v.id = i.issue_id;

-- ---------- reservations for Wings of Fire (edition 13) ----------
-- all its copies are out or on hold, so people queue. queue_no keeps counting
-- even after old reservations close.
INSERT INTO reservation (edition_id, member_id, queue_no, reserved_on, status, copy_id, ready_on) VALUES
(13,  6, 1, DATE_SUB(NOW(), INTERVAL 50 DAY), 'FULFILLED', NULL, NULL),
(13, 11, 2, DATE_SUB(NOW(), INTERVAL 40 DAY), 'CANCELLED', NULL, NULL),
(13,  7, 3, DATE_SUB(NOW(), INTERVAL  9 DAY), 'READY',     29,   DATE_SUB(CURDATE(), INTERVAL 1 DAY)),
(13,  2, 4, DATE_SUB(NOW(), INTERVAL  6 DAY), 'WAITING',   NULL, NULL),
(13,  4, 5, DATE_SUB(NOW(), INTERVAL  2 DAY), 'WAITING',   NULL, NULL);

-- ---------- digital resources ----------
INSERT INTO digital_resource (title, resource_type, publisher_id, url, licence_end) VALUES
('IEEE Xplore Digital Library',       'DATABASE', NULL, 'https://digital.library.example/ieee',        DATE_ADD(CURDATE(), INTERVAL 200 DAY)),
('Database System Concepts (e-book)', 'EBOOK',    2,    'https://digital.library.example/dbsc',        DATE_ADD(CURDATE(), INTERVAL 300 DAY)),
('Learning Python (e-book)',          'EBOOK',    5,    'https://digital.library.example/lpython',     DATE_ADD(CURDATE(), INTERVAL 150 DAY)),
('Journal of Management Studies',     'JOURNAL',  3,    'https://digital.library.example/jms',         DATE_ADD(CURDATE(), INTERVAL 90 DAY)),
('Algorithms Lecture Series',         'VIDEO',    6,    'https://digital.library.example/algo-videos', DATE_ADD(CURDATE(), INTERVAL 365 DAY)),
('Computer Networks Lab Videos',      'VIDEO',    1,    'https://digital.library.example/cn-lab',      DATE_SUB(CURDATE(), INTERVAL 10 DAY));

INSERT INTO digital_access_log (resource_id, member_id, accessed_at, minutes_used) VALUES
(1, 1, DATE_SUB(NOW(), INTERVAL 30 DAY), 45), (1, 2, DATE_SUB(NOW(), INTERVAL 28 DAY), 30),
(1, 3, DATE_SUB(NOW(), INTERVAL 20 DAY), 60), (1, 8, DATE_SUB(NOW(), INTERVAL 18 DAY), 90),
(1, 9, DATE_SUB(NOW(), INTERVAL 12 DAY), 75), (1, 1, DATE_SUB(NOW(), INTERVAL  5 DAY), 40),
(2, 1, DATE_SUB(NOW(), INTERVAL 27 DAY), 120),(2, 4, DATE_SUB(NOW(), INTERVAL 22 DAY), 50),
(2, 5, DATE_SUB(NOW(), INTERVAL 15 DAY), 35), (2, 1, DATE_SUB(NOW(), INTERVAL  3 DAY), 80),
(3, 6, DATE_SUB(NOW(), INTERVAL 25 DAY), 55), (3, 7, DATE_SUB(NOW(), INTERVAL 14 DAY), 65),
(3, 2, DATE_SUB(NOW(), INTERVAL  8 DAY), 20),
(4, 8, DATE_SUB(NOW(), INTERVAL 24 DAY), 25), (4, 9, DATE_SUB(NOW(), INTERVAL 10 DAY), 30),
(4, 10,DATE_SUB(NOW(), INTERVAL  6 DAY), 15),
(5, 3, DATE_SUB(NOW(), INTERVAL 19 DAY), 100),(5, 5, DATE_SUB(NOW(), INTERVAL 11 DAY), 85),
(5, 1, DATE_SUB(NOW(), INTERVAL  7 DAY), 70), (5, 6, DATE_SUB(NOW(), INTERVAL  2 DAY), 95),
(6, 4, DATE_SUB(NOW(), INTERVAL 40 DAY), 45), (6, 7, DATE_SUB(NOW(), INTERVAL 35 DAY), 50),
(2, 11,DATE_SUB(NOW(), INTERVAL  1 DAY), 10), (1, 10,DATE_SUB(NOW(), INTERVAL  1 DAY), 20);
