# Retail Sales Analysis — Chinook sample digital music store

A reproducible entry-level data analyst case study using **SQLite, SQL, Python, pandas and matplotlib**. It analyzes the Chinook sample digital music store database as an educational retail-style dataset. The records are sample/fictitious—not real commercial retail customers or sales.

## Questions answered

1. Do invoice totals reconcile to invoice-line extended values (`UnitPrice × Quantity`)?
2. How many orders are in the sample, what is the average order value, and how does invoice revenue vary by month?
3. Which billing countries contribute the most invoice revenue?
4. How concentrated is revenue across customers, and what share of observed customers/orders are repeat under an explicit definition?
5. Which genres and tracks lead line-item revenue?

## Key results from the reproducible run

The source contains **412 invoices**, **2,240 invoice lines**, and **59 customers with observed orders**, covering **2021-01 through 2025-12**. Recorded invoice revenue is **2,328.60** sample currency units; line-item extended value is **2,328.60**, with an absolute reconciliation difference below one cent. AOV is **5.65**. The United States is the largest billing-country segment at **523.06**. Rock is the largest line-item genre at **826.65**. All 59 observed customers have at least two invoices in this sample window; this is not a retention or churn rate.

Read the fully calculated, cautious interpretation in [`outputs/findings.md`](outputs/findings.md). Numbers above are descriptive outputs from the bundled source and must not be generalized beyond this sample.

### Revenue by billing country

![Top billing countries by invoice revenue](outputs/charts/country_revenue.png)

## Quick start

From this repository root in a clean Python environment:

```bash
python -m pip install -r requirements.txt
python analysis.py
python -m unittest discover -s tests -v
```

`analysis.py` executes the bundled SQL into an in-memory SQLite database, validates it, writes CSV tables, and regenerates the three charts. It does not download anything. A generated database, virtual environment or cache is not required and is excluded by [`.gitignore`](.gitignore).

## What is included

- [`analysis.py`](analysis.py) — reusable analysis, validation, CSV and chart generation script.
- [`sql/analysis_queries.sql`](sql/analysis_queries.sql) — documented SQL with joins, aggregation, date grouping, a CTE and a window function.
- [`tests/test_analysis.py`](tests/test_analysis.py) — straightforward standard-library tests for source counts, reconciliation and artifacts.
- [`outputs/findings.md`](outputs/findings.md) — findings, denominators, cautious recommendations and limitations.
- [`outputs/monthly_sales.csv`](outputs/monthly_sales.csv), [`outputs/country_sales.csv`](outputs/country_sales.csv), [`outputs/genre_sales.csv`](outputs/genre_sales.csv), [`outputs/customer_summary.csv`](outputs/customer_summary.csv), [`outputs/top_tracks.csv`](outputs/top_tracks.csv) — small Excel-openable result tables.
- [`outputs/data_quality.csv`](outputs/data_quality.csv) — actual validation evidence.
- [`outputs/charts/monthly_revenue.png`](outputs/charts/monthly_revenue.png), [`outputs/charts/country_revenue.png`](outputs/charts/country_revenue.png), [`outputs/charts/genre_revenue.png`](outputs/charts/genre_revenue.png) — three static charts.
- [`docs/interview-guide.md`](docs/interview-guide.md) — short explanation of grain, validation and limitations.
- [`data/provenance.md`](data/provenance.md) — source URL, fetched date, Git blob SHA, SHA-256 checksum and license notes.
- [`data/data-dictionary.md`](data/data-dictionary.md) — definitions, grains, joins and derived-measure denominators for analyzed fields.
- [`data/Chinook_Sqlite.sql`](data/Chinook_Sqlite.sql) — source SQL preserved unchanged under its original license; [`data/LICENSE.md`](data/LICENSE.md) preserves the original copyright/permission notice.

## Grain, methods and validation

`Invoice` is one row per order, so invoice revenue, order count and AOV are calculated there. `InvoiceLine` is one row per purchased track on an invoice, so genre and track mix use line-item extended values. The script never sums `Invoice.Total` after joining to lines, which prevents double counting.

The run fails loudly for missing tables, duplicate primary keys, orphan foreign keys, NULL or negative values in modeled money/quantity fields, and invoice-versus-line reconciliation beyond **0.01** currency units. It does not silently drop unknown records.

The source contains no cost, margin, discount, returns, tax, marketing, inventory, currency-conversion or population-denominator fields. Consequently, this project makes no profit, causal, churn, lifetime-value or forecast claims. Billing country is descriptive, not a market-size measure. See [`outputs/findings.md`](outputs/findings.md) for the full caveat set.

## Data source and learning disclosure

Source: [lerocha/chinook-database](https://github.com/lerocha/chinook-database), specifically [`Chinook_Sqlite.sql`](https://github.com/lerocha/chinook-database/blob/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql), fetched 2026-09-14. The original license and provenance are in [`data/provenance.md`](data/provenance.md). The source README is preserved at [`data/SOURCE-README.md`](data/SOURCE-README.md).

This project demonstrates a learning workflow—not employment, certification or prior professional experience. **Learning project prepared with AI assistance; review, reproduce, and adapt before presenting.**
