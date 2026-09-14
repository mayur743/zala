# Data dictionary for analyzed fields

The source schema contains more tables; this dictionary covers fields used by the analysis. Names preserve the source's SQLite casing.

| Table / field | Meaning and use | Analysis note |
|---|---|---|
| `Invoice.InvoiceId` | Invoice/order identifier | Invoice grain; primary key |
| `Invoice.CustomerId` | Customer associated with invoice | Join to `Customer.CustomerId` |
| `Invoice.InvoiceDate` | Invoice timestamp | Grouped to `YYYY-MM` for monthly results |
| `Invoice.BillingCountry` | Billing country stored on invoice | Descriptive billing geography, not market size |
| `Invoice.Total` | Recorded invoice total | Used for order revenue and AOV |
| `InvoiceLine.InvoiceLineId` | Invoice-line identifier | One row per purchased track line; primary key |
| `InvoiceLine.InvoiceId` | Parent invoice identifier | Join to `Invoice.InvoiceId` |
| `InvoiceLine.TrackId` | Purchased track identifier | Join to `Track.TrackId` |
| `InvoiceLine.UnitPrice` | Stored unit price for line | Multiplied by `Quantity` for extended line value |
| `InvoiceLine.Quantity` | Units on the line | Included in extended line value |
| `Customer.CustomerId` | Customer identifier | Customer grain for observed-order customers |
| `Customer.FirstName`, `LastName` | Customer name fields | Display label only; no identity matching |
| `Track.TrackId` | Track identifier | Joins line items to product metadata |
| `Track.Name` | Track title | Used for top-track table |
| `Track.GenreId` | Genre identifier | Left join to `Genre` |
| `Genre.GenreId`, `Genre.Name` | Genre identifier and label | Used for line-item mix |

## Derived measures

- **Line extended value:** `InvoiceLine.UnitPrice × InvoiceLine.Quantity`.
- **AOV:** `SUM(Invoice.Total) / COUNT(Invoice.InvoiceId)`; denominator is invoices/orders.
- **Repeat customer:** a customer with `COUNT(Invoice.InvoiceId) >= 2` in the observed sample period. Repeat-customer rate denominator is customers with at least one invoice.
- **Revenue share:** segment revenue divided by the relevant total: invoice revenue for countries/customers, line-item extended value for genres/tracks.
