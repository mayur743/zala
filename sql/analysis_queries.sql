-- Chinook sample digital-music retail analysis queries.
-- Run against SQLite after executing data/Chinook_Sqlite.sql.
-- Invoice grain is kept separate from line-item grain to avoid double-counting.

-- 1) Invoice-level revenue, order count and AOV.
SELECT COUNT(*) AS order_count,
       ROUND(SUM(Total), 2) AS invoice_revenue,
       ROUND(AVG(Total), 2) AS aov,
       MIN(InvoiceDate) AS first_invoice_date,
       MAX(InvoiceDate) AS last_invoice_date
FROM Invoice;

-- 2) Reconcile invoice totals against line extended values.
WITH line_totals AS (
    SELECT SUM(UnitPrice * Quantity) AS line_revenue
    FROM InvoiceLine
)
SELECT ROUND((SELECT SUM(Total) FROM Invoice), 2) AS invoice_revenue,
       ROUND(line_revenue, 2) AS line_item_revenue,
       ROUND((SELECT SUM(Total) FROM Invoice) - line_revenue, 8) AS difference
FROM line_totals;

-- 3) Monthly invoice revenue. Date grouping is based on InvoiceDate.
SELECT substr(InvoiceDate, 1, 7) AS month,
       COUNT(*) AS orders,
       ROUND(SUM(Total), 2) AS revenue,
       ROUND(AVG(Total), 2) AS aov
FROM Invoice
GROUP BY substr(InvoiceDate, 1, 7)
ORDER BY month;

-- 4) Billing-country performance. Share denominator is all invoice revenue.
SELECT BillingCountry AS country,
       COUNT(*) AS orders,
       ROUND(SUM(Total), 2) AS revenue,
       ROUND(100.0 * SUM(Total) / (SELECT SUM(Total) FROM Invoice), 2) AS revenue_share_pct
FROM Invoice
GROUP BY BillingCountry
ORDER BY revenue DESC, country;

-- 5) Genre mix at invoice-line grain. No profit claim: cost/margin is absent.
SELECT g.Name AS genre,
       COUNT(il.InvoiceLineId) AS line_items,
       ROUND(SUM(il.UnitPrice * il.Quantity), 2) AS revenue,
       ROUND(100.0 * SUM(il.UnitPrice * il.Quantity) /
             (SELECT SUM(UnitPrice * Quantity) FROM InvoiceLine), 2) AS revenue_share_pct
FROM InvoiceLine AS il
JOIN Track AS t ON t.TrackId = il.TrackId
LEFT JOIN Genre AS g ON g.GenreId = t.GenreId
GROUP BY g.GenreId, g.Name
ORDER BY revenue DESC, genre;

-- 6) Customer concentration and repeat classification.
WITH customer_orders AS (
    SELECT c.CustomerId,
           c.FirstName || ' ' || c.LastName AS customer,
           COUNT(i.InvoiceId) AS orders,
           SUM(i.Total) AS revenue
    FROM Customer AS c
    JOIN Invoice AS i ON i.CustomerId = c.CustomerId
    GROUP BY c.CustomerId, customer
), ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (ORDER BY revenue DESC, CustomerId) AS revenue_rank,
           CASE WHEN orders >= 2 THEN 1 ELSE 0 END AS repeat_customer
    FROM customer_orders
)
SELECT CustomerId, customer, orders, ROUND(revenue, 2) AS revenue,
       revenue_rank, repeat_customer,
       ROUND(100.0 * revenue / (SELECT SUM(revenue) FROM customer_orders), 2) AS revenue_share_pct
FROM ranked
ORDER BY revenue_rank;

-- 7) Top tracks by line-item extended value.
SELECT t.Name AS track,
       g.Name AS genre,
       COUNT(il.InvoiceLineId) AS line_items,
       ROUND(SUM(il.UnitPrice * il.Quantity), 2) AS revenue
FROM InvoiceLine AS il
JOIN Track AS t ON t.TrackId = il.TrackId
LEFT JOIN Genre AS g ON g.GenreId = t.GenreId
GROUP BY t.TrackId, t.Name, g.Name
ORDER BY revenue DESC, track
LIMIT 10;
