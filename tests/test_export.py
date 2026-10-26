import sqlite3

import pandas as pd
import pytest

from export_data import build_date_table, export

SCHEMA = """
CREATE TABLE categories (category_id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE products (product_id INTEGER PRIMARY KEY, category_id INTEGER, name TEXT,
                       description TEXT, price REAL, stock INTEGER);
CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT, email TEXT,
                        password_hash TEXT, created_at TEXT);
CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER, total REAL, created_at TEXT);
CREATE TABLE order_items (order_id INTEGER, product_id INTEGER, quantity INTEGER, unit_price REAL);
INSERT INTO categories VALUES (1, 'Coffee'), (2, 'Tea');
INSERT INTO products VALUES (1, 1, 'Coffee A', '', 40.0, 10), (2, 2, 'Tea B', '', 25.5, 5);
INSERT INTO customers VALUES (1, 'Ala', 'a@example.com', 'h', '2026-01-05 10:00:00'),
                             (2, 'Ola', 'o@example.com', 'h', '2026-02-01 10:00:00');
INSERT INTO orders VALUES (1, 1, 105.5, '2026-01-10 12:00:00'), (2, 1, 40.0, '2026-03-02 09:30:00');
INSERT INTO order_items VALUES (1, 1, 2, 40.0), (1, 2, 1, 25.5), (2, 1, 1, 40.0);
"""


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "shop.db"
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
    return path


def test_export_creates_star_schema(db_path, tmp_path):
    tables = export(db_path, tmp_path / "out")
    assert {f.name for f in (tmp_path / "out").iterdir()} == {
        "fact_sales.csv", "dim_product.csv", "dim_customer.csv", "dim_date.csv"}
    fact = tables["fact_sales"]
    assert len(fact) == 3
    assert fact["revenue"].sum() == pytest.approx(145.5)  # matches the order totals


def test_fact_keys_exist_in_dimensions(db_path, tmp_path):
    t = export(db_path, tmp_path)
    assert set(t["fact_sales"]["product_id"]) <= set(t["dim_product"]["product_id"])
    assert set(t["fact_sales"]["customer_id"]) <= set(t["dim_customer"]["customer_id"])
    assert set(pd.to_datetime(t["fact_sales"]["order_date"]).dt.date) <= set(t["dim_date"]["date"])


def test_customer_without_orders_is_kept(db_path, tmp_path):
    customers = export(db_path, tmp_path)["dim_customer"].set_index("customer")
    assert customers.loc["Ola", "orders_count"] == 0
    assert customers.loc["Ala", "first_order_month"] == "2026-01"


def test_date_table_covers_full_years_without_gaps():
    dates = build_date_table(["2026-03-15", "2026-05-01"])
    assert len(dates) == 365
    assert dates.iloc[0]["month_name"] == "January"
    assert dates.iloc[0]["weekday_name"] == "Thursday"  # 1 January 2026 is a Thursday
    assert dates["is_weekend"].sum() == 104


def test_csv_files_have_utf8_bom(db_path, tmp_path):
    export(db_path, tmp_path)
    assert (tmp_path / "dim_date.csv").read_bytes().startswith(b"\xef\xbb\xbf")


def test_empty_database_gives_clear_message(tmp_path):
    path = tmp_path / "empty.db"
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA.split("INSERT")[0])
    with pytest.raises(SystemExit, match="demo-data"):
        export(path, tmp_path / "out")
