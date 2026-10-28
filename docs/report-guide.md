# Building the report in Power BI

You need **Power BI Desktop** (free, Windows only): Microsoft Store → search for "Power BI Desktop" → Get. No account is needed to work locally.

## 1. Load the data
1. **Home → Get data → Text/CSV**, choose `data/fact_sales.csv` → **Transform Data** (opens Power Query).
2. Check the column types: `order_date` = **Date**, `revenue` and `unit_price` = **Decimal number**, the rest = **Whole number**. If prices show up as text, use **Change type → Using locale → English (United States)**, because the files use a decimal point.
3. **New Source → Text/CSV** and add `dim_product.csv`, `dim_customer.csv` and `dim_date.csv` the same way. In `dim_date`, `date` must be **Date** and `is_weekend` **True/False**.
4. **Close & Apply**.

## 2. Data model (star schema)
1. Open the **Model** view.
2. Create the relationships (many-to-one, single filter direction) by dragging one column onto the other:
   - `fact_sales[product_id]` → `dim_product[product_id]`
   - `fact_sales[customer_id]` → `dim_customer[customer_id]`
   - `fact_sales[order_date]` → `dim_date[date]`
3. Select `dim_date` → **Table tools → Mark as date table** → column `date`. Time intelligence measures need this.
4. Sort `dim_date[month_name]` by `month_number` and `weekday_name` by `weekday_number` (**Column tools → Sort by column**), otherwise they sort alphabetically.
5. Hide the key columns in `fact_sales` (`product_id`, `customer_id`, `order_date`) from the report view.

## 3. Measures
Add every measure from [`measures.dax`](../measures.dax) to `fact_sales` (**New measure**). Formatting:
- `Total Revenue`, `Avg Order Value`, `Revenue per Customer`, `Revenue Prev Month`, `Revenue YTD`, `7-Day Avg`: **Currency** (PLN), 2 decimals
- `MoM %`, `Revenue Share %`, `Weekend Revenue %`: **Percentage**, 1 decimal

## 4. Page "Overview"
| Visual | Fields |
|---|---|
| 4 × **Card** | `Total Revenue`, `Orders`, `Avg Order Value`, `Buying Customers` |
| **Line and clustered column chart** | X-axis: `dim_date[year_month]`; columns: `Total Revenue`; line: `MoM %` |
| **Line chart** | X-axis: `dim_date[date]`; values: `7-Day Avg` |
| **Slicer** | `dim_product[category]` |
| **Slicer** | `dim_date[month_name]` |

## 5. Page "Products"
| Visual | Fields |
|---|---|
| **Donut chart** | legend: `dim_product[category]`; values: `Total Revenue` |
| **Table** | `dim_product[product]`, `Product Rank`, `Total Revenue`, `Units Sold`, `Revenue Share %`, `dim_product[stock]` (conditional formatting: red background when stock < 10) |
| **Bar chart** | Y-axis: `dim_product[product]`; values: `Total Revenue`; filter **Top N = 5** by `Total Revenue` |

## 6. Page "Customers"
| Visual | Fields |
|---|---|
| 3 × **Card** | `Revenue per Customer`, `Loyal Customers (12+ orders)`, `Weekend Revenue %` |
| **Column chart** | X-axis: `dim_date[weekday_name]`; values: `Total Revenue` |
| **Table** | `dim_customer[customer]`, `dim_customer[signup_date]`, `dim_customer[orders_count]`, `Total Revenue` (sorted descending) |
| **Matrix** (cohorts) | rows: `dim_customer[first_order_month]`; columns: `dim_date[year_month]`; values: `Buying Customers` |

## 7. Save and share
1. **File → Save as** → `sales-dashboard.pbix` in the repository root.
2. Take a screenshot of the model and each page: `screenshots/model.png`, `overview.png`, `products.png`, `customers.png`.
3. **File → Export → Export to PDF** → `sales-dashboard.pdf`, so the report can be viewed without Power BI.

## Refreshing the data
1. Export a fresh copy of the shop database, e.g. `docker compose cp shop:/app/instance/shop.db ./shop.db` in the `flask-sql-shop` folder.
2. `python export_data.py --db path/to/shop.db --out data`
3. In Power BI: **Home → Refresh**.
