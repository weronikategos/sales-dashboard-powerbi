"""Exports sales data from the flask-sql-shop database to CSV files in a star schema for Power BI.

Star schema: one fact table with the sales and dimension tables used for filtering
and grouping (product, customer, date).
"""
import argparse
import sqlite3
from pathlib import Path

import pandas as pd

FACT_SALES_SQL = """
SELECT oi.order_id,
       DATE(o.created_at)                     AS order_date,
       o.customer_id,
       oi.product_id,
       oi.quantity,
       oi.unit_price,
       ROUND(oi.quantity * oi.unit_price, 2)  AS revenue
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
ORDER BY o.created_at, oi.order_id
"""

DIM_PRODUCT_SQL = """
SELECT p.product_id, p.name AS product, c.name AS category, p.price AS list_price, p.stock
FROM products p JOIN categories c ON c.category_id = p.category_id
ORDER BY p.product_id
"""

# Cohort = the month of the customer's first order (to see whether customers come back)
DIM_CUSTOMER_SQL = """
SELECT c.customer_id,
       c.name                                     AS customer,
       DATE(c.created_at)                         AS signup_date,
       STRFTIME('%Y-%m', MIN(o.created_at))       AS first_order_month,
       COUNT(o.order_id)                          AS orders_count
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id
ORDER BY c.customer_id
"""

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def build_date_table(dates):
    """Date table from Jan 1 to Dec 31 of the years with sales, with no gaps."""
    dates = pd.to_datetime(dates)
    days = pd.date_range(f"{dates.min().year}-01-01", f"{dates.max().year}-12-31", freq="D")
    return pd.DataFrame({
        "date": days.date,
        "year": days.year,
        "quarter": "Q" + days.quarter.astype(str),
        "month_number": days.month,
        "month_name": [MONTHS[m - 1] for m in days.month],
        "year_month": days.strftime("%Y-%m"),
        "weekday_number": days.weekday + 1,
        "weekday_name": [WEEKDAYS[d] for d in days.weekday],
        "is_weekend": days.weekday >= 5,
    })


def export(db_path, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        fact = pd.read_sql_query(FACT_SALES_SQL, conn)
        if fact.empty:
            raise SystemExit("There are no orders in the database. Run this in the shop: flask --app shop demo-data")
        tables = {
            "fact_sales": fact,
            "dim_product": pd.read_sql_query(DIM_PRODUCT_SQL, conn),
            "dim_customer": pd.read_sql_query(DIM_CUSTOMER_SQL, conn),
            "dim_date": build_date_table(fact["order_date"]),
        }
    for name, df in tables.items():
        # utf-8-sig adds a BOM, so Excel and Power BI detect the encoding correctly
        df.to_csv(out / f"{name}.csv", index=False, encoding="utf-8-sig")
        print(f"{name}.csv: {len(df)} rows")
    return tables


def main():
    parser = argparse.ArgumentParser(description="Export sales data to CSV for Power BI")
    parser.add_argument("--db", required=True, help="path to shop.db (e.g. ../flask-sql-shop/instance/shop.db)")
    parser.add_argument("--out", default="data", help="folder for the CSV files")
    args = parser.parse_args()
    export(args.db, args.out)


if __name__ == "__main__":
    main()
