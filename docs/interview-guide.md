# Interview guide

## Explain the grain first

`Invoice` is one row per order and `InvoiceLine` is one row per purchased track on an order. I calculate order count, invoice revenue and AOV from `Invoice`. I calculate genre and track mix from `InvoiceLine` using `UnitPrice * Quantity`. I never sum `Invoice.Total` after joining to lines, because that would repeat each invoice once per line.

## Explain the validation

I execute the supplied SQLite script in memory, check expected tables, duplicate primary keys, orphan foreign keys, NULL and negative values in money/quantity fields, and reconcile invoice totals to line extended values within one cent. A failed check stops the run instead of silently dropping records.

## Explain the repeat metric

A repeat customer is a customer with at least two invoices in the observed sample window. The denominator is the 59 customers with at least one invoice, not all possible customers. This is not a cohort-retention, churn or lifetime-value measure.

## Explain limitations

The Chinook records are sample/fictitious educational data. There are no costs, margins, refunds, taxes, marketing exposures, inventory measures, currency conversions or market-size denominators. Therefore the project reports descriptive revenue and mix only; it does not claim profit, causality or future performance.
