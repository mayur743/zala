#!/usr/bin/env python3
"""Reproducible Chinook sample digital-music retail analysis.

Run from this repository's root: python analysis.py
The source SQL is executed in an in-memory SQLite database; no generated DB is
needed in the repository.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent
SQL_SOURCE = ROOT / "data" / "Chinook_Sqlite.sql"
OUT = ROOT / "outputs"
CHARTS = OUT / "charts"
TOLERANCE = 0.01


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SQL_SOURCE.read_text(encoding="utf-8"))
    return conn


def table_names(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]


def quality_checks(conn: sqlite3.Connection) -> pd.DataFrame:
    """Run explicit baseline checks; any failed check raises before outputs update."""
    checks: list[dict[str, object]] = []
    expected_tables = ["Album", "Artist", "Customer", "Employee", "Genre", "Invoice", "InvoiceLine", "MediaType", "Playlist", "PlaylistTrack", "Track"]
    for table in expected_tables:
        checks.append({"check": f"table_present:{table}", "observed": int(table in table_names(conn)), "status": "PASS" if table in table_names(conn) else "FAIL", "note": "Expected Chinook table exists"})

    pk_specs = {
        "Album": "AlbumId", "Artist": "ArtistId", "Customer": "CustomerId", "Employee": "EmployeeId",
        "Genre": "GenreId", "Invoice": "InvoiceId", "InvoiceLine": "InvoiceLineId", "MediaType": "MediaTypeId",
        "Playlist": "PlaylistId", "Track": "TrackId",
    }
    for table, pk in pk_specs.items():
        n, distinct_n = conn.execute(f'SELECT COUNT("{pk}"), COUNT(DISTINCT "{pk}") FROM "{table}"').fetchone()
        checks.append({"check": f"duplicate_pk:{table}.{pk}", "observed": int(n - distinct_n), "status": "PASS" if n == distinct_n else "FAIL", "note": "duplicate count; expected 0"})
    n, distinct_n = conn.execute("SELECT COUNT(*), COUNT(DISTINCT PlaylistId || ':' || TrackId) FROM PlaylistTrack").fetchone()
    checks.append({"check": "duplicate_pk:PlaylistTrack.(PlaylistId,TrackId)", "observed": int(n - distinct_n), "status": "PASS" if n == distinct_n else "FAIL", "note": "duplicate composite-key count; expected 0"})

    fk_specs = [
        ("Invoice", "CustomerId", "Customer", "CustomerId"),
        ("InvoiceLine", "InvoiceId", "Invoice", "InvoiceId"),
        ("InvoiceLine", "TrackId", "Track", "TrackId"),
        ("Track", "AlbumId", "Album", "AlbumId"),
        ("Track", "MediaTypeId", "MediaType", "MediaTypeId"),
        ("Track", "GenreId", "Genre", "GenreId"),
        ("Customer", "SupportRepId", "Employee", "EmployeeId"),
        ("Album", "ArtistId", "Artist", "ArtistId"),
        ("PlaylistTrack", "PlaylistId", "Playlist", "PlaylistId"),
        ("PlaylistTrack", "TrackId", "Track", "TrackId"),
    ]
    for child, col, parent, parent_col in fk_specs:
        n = conn.execute(f'''SELECT COUNT(*) FROM "{child}" c LEFT JOIN "{parent}" p ON c."{col}" = p."{parent_col}" WHERE c."{col}" IS NOT NULL AND p."{parent_col}" IS NULL''').fetchone()[0]
        checks.append({"check": f"orphan_fk:{child}.{col}->{parent}.{parent_col}", "observed": int(n), "status": "PASS" if n == 0 else "FAIL", "note": "orphan count; expected 0"})

    numeric_specs = [("Invoice", "Total"), ("InvoiceLine", "UnitPrice"), ("InvoiceLine", "Quantity"), ("Track", "UnitPrice")]
    for table, col in numeric_specs:
        nulls = conn.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{col}" IS NULL').fetchone()[0]
        negatives = conn.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{col}" < 0').fetchone()[0]
        checks.append({"check": f"null_numeric:{table}.{col}", "observed": int(nulls), "status": "PASS" if nulls == 0 else "FAIL", "note": "NULL count; expected 0"})
        checks.append({"check": f"negative_numeric:{table}.{col}", "observed": int(negatives), "status": "PASS" if negatives == 0 else "FAIL", "note": "negative count; expected 0 for this case study"})

    result = pd.DataFrame(checks, columns=["check", "observed", "status", "note"])
    if not (result["status"] == "PASS").all():
        failed = result.loc[result["status"] != "PASS"].to_dict("records")
        raise RuntimeError(f"Data-quality validation failed: {failed}")
    return result


def build_outputs(conn: sqlite3.Connection) -> dict[str, float | int | str]:
    quality = quality_checks(conn)
    invoices = pd.read_sql_query("SELECT * FROM Invoice", conn)
    lines = pd.read_sql_query("SELECT * FROM InvoiceLine", conn)

    invoice_total = float(invoices["Total"].sum())
    line_total = float((lines["UnitPrice"] * lines["Quantity"]).sum())
    difference = invoice_total - line_total
    if abs(difference) > TOLERANCE:
        raise RuntimeError(f"Invoice/line reconciliation exceeded ${TOLERANCE:.2f}: {difference}")

    # The join to line items is only used for line-level metrics. Invoice-level
    # metrics always aggregate Invoice directly, preventing line multiplication.
    monthly = pd.read_sql_query("""
        SELECT substr(InvoiceDate, 1, 7) AS month,
               COUNT(*) AS orders,
               ROUND(SUM(Total), 2) AS revenue,
               ROUND(AVG(Total), 2) AS aov
        FROM Invoice
        GROUP BY substr(InvoiceDate, 1, 7)
        ORDER BY month
    """, conn)
    country = pd.read_sql_query("""
        SELECT BillingCountry AS country,
               COUNT(*) AS orders,
               ROUND(SUM(Total), 2) AS revenue,
               ROUND(100.0 * SUM(Total) / (SELECT SUM(Total) FROM Invoice), 2) AS revenue_share_pct
        FROM Invoice
        GROUP BY BillingCountry
        ORDER BY revenue DESC, country
    """, conn)
    genre = pd.read_sql_query("""
        SELECT g.Name AS genre,
               COUNT(il.InvoiceLineId) AS line_items,
               ROUND(SUM(il.UnitPrice * il.Quantity), 2) AS revenue,
               ROUND(100.0 * SUM(il.UnitPrice * il.Quantity) / (SELECT SUM(UnitPrice * Quantity) FROM InvoiceLine), 2) AS revenue_share_pct
        FROM InvoiceLine il
        JOIN Track t ON t.TrackId = il.TrackId
        LEFT JOIN Genre g ON g.GenreId = t.GenreId
        GROUP BY g.GenreId, g.Name
        ORDER BY revenue DESC, genre
    """, conn)
    customer = pd.read_sql_query("""
        WITH customer_orders AS (
            SELECT c.CustomerId,
                   c.FirstName || ' ' || c.LastName AS customer,
                   COUNT(i.InvoiceId) AS orders,
                   ROUND(SUM(i.Total), 2) AS revenue
            FROM Customer c
            JOIN Invoice i ON i.CustomerId = c.CustomerId
            GROUP BY c.CustomerId, customer
        )
        SELECT CustomerId, customer, orders, revenue,
               ROUND(100.0 * revenue / (SELECT SUM(revenue) FROM customer_orders), 2) AS revenue_share_pct,
               CASE WHEN orders >= 2 THEN 1 ELSE 0 END AS repeat_customer
        FROM customer_orders
        ORDER BY revenue DESC, CustomerId
    """, conn)
    top_tracks = pd.read_sql_query("""
        SELECT t.Name AS track, g.Name AS genre,
               COUNT(il.InvoiceLineId) AS line_items,
               ROUND(SUM(il.UnitPrice * il.Quantity), 2) AS revenue
        FROM InvoiceLine il
        JOIN Track t ON t.TrackId = il.TrackId
        LEFT JOIN Genre g ON g.GenreId = t.GenreId
        GROUP BY t.TrackId, t.Name, g.Name
        ORDER BY revenue DESC, track
        LIMIT 10
    """, conn)

    quality = quality.copy()
    quality.loc[len(quality)] = ["invoice_line_reconciliation_cents", round(abs(difference) * 100, 8), "PASS", "absolute difference; expected <= 1 cent"]
    quality.loc[len(quality)] = ["invoice_count", int(len(invoices)), "PASS", "one row is one invoice/order"]
    quality.loc[len(quality)] = ["invoice_line_count", int(len(lines)), "PASS", "one row is one purchased line item"]

    OUT.mkdir(exist_ok=True)
    CHARTS.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(OUT / "monthly_sales.csv", index=False)
    country.to_csv(OUT / "country_sales.csv", index=False)
    genre.to_csv(OUT / "genre_sales.csv", index=False)
    customer.to_csv(OUT / "customer_summary.csv", index=False)
    top_tracks.to_csv(OUT / "top_tracks.csv", index=False)
    quality.to_csv(OUT / "data_quality.csv", index=False)

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(monthly["month"], monthly["revenue"], marker="o", linewidth=1.8, color="#155e75")
    ax.set(title="Monthly invoice revenue", xlabel="Invoice month", ylabel="Revenue (sample currency units)")
    ax.tick_params(axis="x", rotation=60, labelsize=8)
    fig.tight_layout(); fig.savefig(CHARTS / "monthly_revenue.png", dpi=150, metadata={"Title": "Monthly invoice revenue"}); plt.close(fig)

    top_country = country.head(10).sort_values("revenue")
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.barh(top_country["country"], top_country["revenue"], color="#0e7490")
    ax.set(title="Top 10 billing countries by invoice revenue", xlabel="Revenue (sample currency units)", ylabel="Billing country")
    fig.tight_layout(); fig.savefig(CHARTS / "country_revenue.png", dpi=150, metadata={"Title": "Top billing countries"}); plt.close(fig)

    top_genre = genre.head(10).sort_values("revenue")
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.barh(top_genre["genre"].fillna("Unknown"), top_genre["revenue"], color="#7c3aed")
    ax.set(title="Top 10 genres by line-item revenue", xlabel="Line-item revenue (sample currency units)", ylabel="Genre")
    fig.tight_layout(); fig.savefig(CHARTS / "genre_revenue.png", dpi=150, metadata={"Title": "Top genres"}); plt.close(fig)

    repeat_customers = int((customer["repeat_customer"] == 1).sum())
    total_customers = int(len(customer))
    repeat_invoices = int(invoices[invoices["CustomerId"].isin(customer.loc[customer["repeat_customer"] == 1, "CustomerId"])] .shape[0])
    top10_share = float(customer.head(10)["revenue"].sum() / invoice_total * 100)
    first_month = str(monthly.iloc[0]["month"])
    last_month = str(monthly.iloc[-1]["month"])
    headline: dict[str, float | int | str] = {
        "invoice_count": int(len(invoices)), "line_item_count": int(len(lines)), "customer_count_with_orders": total_customers,
        "invoice_revenue": round(invoice_total, 2), "line_item_revenue": round(line_total, 2), "reconciliation_difference": difference,
        "aov": round(float(invoices["Total"].mean()), 2), "date_start": first_month, "date_end": last_month,
        "repeat_customer_count": repeat_customers, "repeat_customer_rate_pct": round(100 * repeat_customers / total_customers, 2),
        "repeat_invoice_rate_pct": round(100 * repeat_invoices / len(invoices), 2), "top10_customer_revenue_share_pct": round(top10_share, 2),
        "top_country": str(country.iloc[0]["country"]), "top_country_revenue": float(country.iloc[0]["revenue"]),
        "top_genre": str(genre.iloc[0]["genre"]), "top_genre_revenue": float(genre.iloc[0]["revenue"]),
    }
    top5_country = country.head(5)
    top_genre_row = genre.iloc[0]
    top_track_row = top_tracks.iloc[0]
    top_track_revenue = float(top_track_row["revenue"])
    tied_top_tracks = top_tracks[top_tracks["revenue"] == top_track_revenue]
    tied_track_names = ", ".join(f"**{name}**" for name in tied_top_tracks["track"])
    track_tie_text = (
        f"The top purchased tracks tie at **{top_track_revenue:,.2f}**: {tied_track_names}. "
        f"Each appears across **{int(top_track_row['line_items'])} line items**."
        if len(tied_top_tracks) > 1 else
        f"The top purchased track is **{str(top_track_row['track'])}** at **{top_track_revenue:,.2f}** "
        f"across **{int(top_track_row['line_items'])} line items**."
    )
    findings = f"""# Findings — Retail Sales Analysis

## Scope and grain

This analysis uses the Chinook **sample digital music store** database, not real commercial retail data. It covers {headline['invoice_count']:,} invoices/orders and {headline['line_item_count']:,} invoice-line purchases from {headline['date_start']} through {headline['date_end']}. The analysis date is the invoice date; no inference is made outside this range. Currency units are reported as stored in the sample and are not converted or labelled as a specific real-world currency.

- **Invoice grain:** one row per order/invoice. Revenue, order count and average order value (AOV) use this table directly.
- **Invoice-line grain:** one row per purchased track on an invoice. Genre and track mix use line-item extended value (`UnitPrice × Quantity`).
- **Customer grain:** one row per customer with at least one invoice in this sample. Repeat means at least two invoices in this observed window.

## Headline results

- Invoice totals sum to **{headline['invoice_revenue']:,.2f}**; line-item extended values sum to **{headline['line_item_revenue']:,.2f}**. The absolute difference is **{abs(difference):.12f}**, within the **{TOLERANCE:.2f}** currency-unit tolerance. This reconciliation supports using line items for mix while avoiding duplicated invoice totals in joins.
- There are **{headline['invoice_count']:,} orders** and an AOV of **{headline['aov']:,.2f}** (`invoice revenue / invoice count`).
- The top billing country is **{headline['top_country']}** at **{headline['top_country_revenue']:,.2f}**, or **{float(country.iloc[0]['revenue_share_pct']):.2f}%** of invoice revenue. The five largest countries together contribute **{float(top5_country['revenue'].sum() / invoice_total * 100):.2f}%**.
- **{headline['top_genre']}** is the largest genre by line-item revenue at **{headline['top_genre_revenue']:,.2f}**, or **{float(top_genre_row['revenue_share_pct']):.2f}%** of line-item revenue. This is product mix, not profitability: the dataset has no cost or margin field.
- {track_tie_text} Track-level ranking is descriptive and does not measure profit or popularity outside this sample.
- **{headline['repeat_customer_rate_pct']:.2f}%** of the {total_customers} customers with observed orders have at least two invoices ({repeat_customers}/{total_customers}); **{headline['repeat_invoice_rate_pct']:.2f}%** of invoices belong to those repeat customers ({repeat_invoices}/{len(invoices)}). This describes this sample's observed customer history, not a retention or churn rate.
- The top 10 customers account for **{headline['top10_customer_revenue_share_pct']:.2f}%** of invoice revenue. This is concentration within the sample, not a forecast.

## Business implications (cautious)

1. **Prioritize geographic context before action.** The United States leads the billing-country table, but the sample has no acquisition cost, delivery cost, marketing exposure or market-size denominator. Use this as a descriptive starting point for segment review, not proof that a country is more attractive.
2. **Use genre mix to guide merchandising questions.** {headline['top_genre']} leads line-item revenue. A next step would be to inspect availability, pricing and promotion performance with a controlled comparison; this dataset cannot establish causality or profit.
3. **Treat concentration as a monitoring signal.** The top-10 share is worth tracking in a fuller customer-value review, but no churn, lifetime value or future revenue claim is supported by this one sample.

## Reproduce

From the repository root in a clean Python environment:

```bash
python -m pip install -r requirements.txt
python analysis.py
python -m unittest discover -s tests -v
```

The script executes `data/Chinook_Sqlite.sql` into an in-memory SQLite database, runs validation checks, writes CSV tables and regenerates the three PNG charts. It has no network dependency. Run it from the root so relative paths and outputs are predictable.

## Methods and checks

- SQL is documented in [`sql/analysis_queries.sql`](../sql/analysis_queries.sql), including a CTE, a window function, joins, aggregation and date grouping.
- Checks fail loudly for missing tables, duplicate primary keys, orphan foreign keys, NULL/negative numeric values in the modeled money/quantity fields, and invoice-versus-line reconciliation beyond one cent.
- The invoice/line reconciliation is based on `SUM(Invoice.Total)` versus `SUM(InvoiceLine.UnitPrice × InvoiceLine.Quantity)`. Invoice metrics never sum invoice totals after joining lines.
- CSV outputs are Excel-openable: [`monthly_sales.csv`](monthly_sales.csv), [`country_sales.csv`](country_sales.csv), [`genre_sales.csv`](genre_sales.csv), [`customer_summary.csv`](customer_summary.csv), and [`top_tracks.csv`](top_tracks.csv). Validation evidence is [`data_quality.csv`](data_quality.csv).

## Charts

- ![Monthly invoice revenue](charts/monthly_revenue.png)
- ![Top billing countries](charts/country_revenue.png)
- ![Top genres](charts/genre_revenue.png)

## Data source, license and caveats

Source: [lerocha/chinook-database](https://github.com/lerocha/chinook-database), specifically [`Chinook_Sqlite.sql`](https://github.com/lerocha/chinook-database/blob/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql), fetched 2026-09-14. The source repository describes Chinook as a sample database; customer, invoice and music-store records are sample/fictitious educational data. They should not be presented as real retail customers or commercial performance. The original MIT-style permission notice is preserved in [`data/LICENSE.md`](../data/LICENSE.md), and source provenance is documented in [`data/provenance.md`](../data/provenance.md). The source SQL is bundled unchanged for reproducibility.

Important limitations: no cost, margin, discount, returns, tax, marketing, inventory, currency conversion or population denominators are present. `Invoice.Total` is treated as the recorded order total. Country is billing country, not necessarily customer residence or market location. Repeat-customer results are conditional on customers appearing in this sample and its observed dates; they are not cohort retention. No causal, profit, churn, or extrapolated claims are made.

## Skills demonstrated and learning context

This learning project demonstrates a reproducible workflow with SQLite, SQL joins/CTEs/window functions, pandas, matplotlib, data-quality validation, reconciliation, aggregation, CSV reporting and cautious interpretation. It is not a claim of employment, certification or prior professional experience. **Learning project prepared with AI assistance; review, reproduce, and adapt before presenting.**
"""
    (OUT / "findings.md").write_text(findings, encoding="utf-8")
    return headline


def main() -> None:
    conn = connect()
    try:
        headline = build_outputs(conn)
    finally:
        conn.close()
    print("Analysis completed")
    for key in sorted(headline):
        print(f"{key}={headline[key]}")


if __name__ == "__main__":
    main()
