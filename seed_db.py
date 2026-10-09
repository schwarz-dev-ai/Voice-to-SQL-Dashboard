"""Create and seed the mock ``ecommerce.db`` SQLite database.

Run this once before starting the Streamlit app::

    python seed_db.py

Re-running the script rebuilds the database from scratch, so it is safe to use
whenever you want a clean dataset.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "ecommerce.db"

SCHEMA = """
CREATE TABLE customers (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    email       TEXT    NOT NULL UNIQUE,
    country     TEXT    NOT NULL,
    signup_date TEXT    NOT NULL
);

CREATE TABLE products (
    id       INTEGER PRIMARY KEY,
    name     TEXT    NOT NULL,
    category TEXT    NOT NULL,
    price    REAL    NOT NULL,
    stock    INTEGER NOT NULL
);

CREATE TABLE orders (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL,
    order_date  TEXT    NOT NULL
);
"""

# (id, name, email, country, signup_date)
CUSTOMERS = [
    (1, "Ava Thompson", "ava.thompson@example.com", "USA", "2023-01-15"),
    (2, "Liam Müller", "liam.mueller@example.com", "Germany", "2023-02-03"),
    (3, "Sophia Rossi", "sophia.rossi@example.com", "Italy", "2023-02-27"),
    (4, "Noah Kim", "noah.kim@example.com", "South Korea", "2023-03-19"),
    (5, "Emma Dubois", "emma.dubois@example.com", "France", "2023-04-05"),
    (6, "Oliver Smith", "oliver.smith@example.com", "UK", "2023-04-22"),
    (7, "Mia García", "mia.garcia@example.com", "Spain", "2023-05-11"),
    (8, "Ethan Brown", "ethan.brown@example.com", "Canada", "2023-06-02"),
    (9, "Isabella Costa", "isabella.costa@example.com", "Brazil", "2023-06-28"),
    (10, "Lucas Novak", "lucas.novak@example.com", "Czechia", "2023-07-14"),
    (11, "Harper Wilson", "harper.wilson@example.com", "Australia", "2023-08-09"),
    (12, "Yuki Tanaka", "yuki.tanaka@example.com", "Japan", "2023-09-01"),
    (13, "Amelia Jones", "amelia.jones@example.com", "UK", "2023-09-25"),
    (14, "Mateo Fernández", "mateo.fernandez@example.com", "Mexico", "2023-10-17"),
    (15, "Charlotte Meyer", "charlotte.meyer@example.com", "Netherlands", "2023-11-06"),
]

# (id, name, category, price, stock)
PRODUCTS = [
    (1, "Aurora Wireless Headphones", "Electronics", 129.99, 42),
    (2, "Nimbus Bluetooth Speaker", "Electronics", 59.50, 88),
    (3, "Vertex 4K Monitor", "Electronics", 349.00, 15),
    (4, "Pebble Smartwatch", "Electronics", 199.95, 30),
    (5, "Drift Mechanical Keyboard", "Electronics", 89.99, 54),
    (6, "Cobalt Espresso Machine", "Home", 249.00, 12),
    (7, "Lumen Desk Lamp", "Home", 39.99, 120),
    (8, "Willow Ceramic Dinner Set", "Home", 79.95, 36),
    (9, "Summit Cast Iron Pan", "Home", 54.25, 64),
    (10, "Atlas Yoga Mat", "Sports", 34.99, 150),
    (11, "Ridge Trail Backpack", "Sports", 119.00, 27),
    (12, "Pulse Running Shoes", "Sports", 139.99, 48),
    (13, "Fable Paperback Collection", "Books", 44.90, 75),
    (14, "Beacon Cookbook", "Books", 27.50, 90),
    (15, "Harbor Cotton Hoodie", "Clothing", 64.00, 58),
]

# (id, customer_id, product_id, quantity, order_date)
ORDERS = [
    (1, 1, 1, 1, "2024-01-08"),
    (2, 2, 3, 1, "2024-01-15"),
    (3, 3, 6, 1, "2024-01-23"),
    (4, 1, 5, 2, "2024-02-02"),
    (5, 4, 4, 1, "2024-02-14"),
    (6, 5, 12, 1, "2024-02-21"),
    (7, 6, 2, 3, "2024-03-04"),
    (8, 7, 10, 2, "2024-03-12"),
    (9, 8, 11, 1, "2024-03-19"),
    (10, 9, 7, 4, "2024-04-06"),
    (11, 10, 13, 2, "2024-04-18"),
    (12, 11, 8, 1, "2024-04-27"),
    (13, 12, 9, 1, "2024-05-09"),
    (14, 13, 15, 2, "2024-05-20"),
    (15, 14, 14, 3, "2024-06-01"),
    (16, 15, 3, 2, "2024-06-11"),
    (17, 2, 12, 1, "2024-07-03"),
    (18, 4, 6, 1, "2024-07-19"),
    (19, 1, 13, 5, "2024-08-05"),
    (20, 3, 1, 1, "2024-08-22"),
]


def seed(db_path: Path = DB_PATH) -> Path:
    """(Re)build the database at ``db_path`` and populate it with mock data."""
    db_path.unlink(missing_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?)", CUSTOMERS)
        conn.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?)", PRODUCTS)
        conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", ORDERS)
        conn.commit()

    return db_path


if __name__ == "__main__":
    path = seed()
    print(f"Created {path.name}")
    print(f"  customers: {len(CUSTOMERS)} rows")
    print(f"  products:  {len(PRODUCTS)} rows")
    print(f"  orders:    {len(ORDERS)} rows")
