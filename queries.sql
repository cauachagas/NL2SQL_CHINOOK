-- Query 1: Top 10 Clientes que mais gastou
-- Identifica os clientes com os maiores gastos totais, incluindo número de transações e o período analisado.
SELECT
    c.CustomerId,
    c.FirstName || ' ' || c.LastName AS CustomerName,
    '$' || printf('%.2f', SUM(i.Total)) AS TotalSpent,
    COUNT(i.InvoiceId) AS NumberOfTransactions,
    MIN(i.InvoiceDate) AS FirstPurchase,
    MAX(i.InvoiceDate) AS LastPurchase
FROM
    customers c
JOIN
    invoices i ON c.CustomerId = i.CustomerId
GROUP BY
    c.CustomerId
ORDER BY
    SUM(i.Total) DESC
LIMIT 10;

-- Query 2: Top 10 Countries with the highest revenue
-- Determines the countries with the highest total revenue, including the number of sales and unique customers.
SELECT
    i.BillingCountry AS Country,
    '$' || printf('%.2f', SUM(i.Total)) AS TotalRevenue,
    COUNT(i.InvoiceId) AS NumberOfSales,
    COUNT(DISTINCT i.CustomerId) AS UniqueCustomers
FROM
    invoices i
GROUP BY
    i.BillingCountry
ORDER BY
    SUM(i.Total) DESC
LIMIT 10;


-- Query 3: Top 10 Artists with the most units sold
-- Identifies the artists with the highest total units sold, including the revenue generated and the number of albums.
SELECT
    ar.ArtistId,
    ar.Name AS ArtistName,
    COUNT(it.TrackId) AS TotalTracksSold,
    '$' || printf('%.2f', SUM(it.UnitPrice * it.Quantity)) AS TotalRevenue,
    COUNT(DISTINCT al.AlbumId) AS NumberOfAlbums
FROM
    artists ar
JOIN
    albums al ON ar.ArtistId = al.ArtistId
JOIN
    tracks t ON al.AlbumId = t.AlbumId
JOIN
    invoice_items it ON t.TrackId = it.TrackId
GROUP BY
    ar.ArtistId
ORDER BY
    TotalTracksSold DESC
LIMIT 10;
