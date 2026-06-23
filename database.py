import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "sales.db"

ORDER_STATUSES = ("ახალი", "გაგზავნილი", "მიწოდებული", "გაუქმებული")
PAYMENT_STATUSES = ("გადაუხდელი", "გადახდილი")
COMPLETED_ORDER_STATUSES = ("მიწოდებული", "ჩაბარდა")


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _migrate_orders_table(conn: sqlite3.Connection):
    columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)").fetchall()}
    migrations = [
        ("delivery_fee", "ALTER TABLE orders ADD COLUMN delivery_fee REAL NOT NULL DEFAULT 0"),
        ("total_discount", "ALTER TABLE orders ADD COLUMN total_discount REAL NOT NULL DEFAULT 0"),
        ("total_collected", "ALTER TABLE orders ADD COLUMN total_collected REAL NOT NULL DEFAULT 0"),
        ("shipping_charged", "ALTER TABLE orders ADD COLUMN shipping_charged REAL NOT NULL DEFAULT 0"),
        ("actual_delivery_cost", "ALTER TABLE orders ADD COLUMN actual_delivery_cost REAL NOT NULL DEFAULT 0"),
        ("net_product_revenue", "ALTER TABLE orders ADD COLUMN net_product_revenue REAL NOT NULL DEFAULT 0"),
        ("is_deleted", "ALTER TABLE orders ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0"),
        ("payment_alert_sent", "ALTER TABLE orders ADD COLUMN payment_alert_sent INTEGER NOT NULL DEFAULT 0"),
        ("telegram_alert_sent", "ALTER TABLE orders ADD COLUMN telegram_alert_sent INTEGER NOT NULL DEFAULT 0"),
    ]
    for column, sql in migrations:
        if column not in columns:
            conn.execute(sql)

    conn.execute(
        """
        UPDATE orders
        SET
            total_collected = CASE WHEN total_collected = 0 THEN total_amount ELSE total_collected END,
            net_product_revenue = CASE
                WHEN net_product_revenue = 0
                THEN total_amount - COALESCE(actual_delivery_cost, delivery_fee, 0)
                ELSE net_product_revenue
            END
        WHERE total_collected = 0 OR net_product_revenue = 0
        """
    )


def _migrate_products_table(conn: sqlite3.Connection):
    columns = {row[1] for row in conn.execute("PRAGMA table_info(products)").fetchall()}
    if "is_deleted" not in columns:
        conn.execute(
            "ALTER TABLE products ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0"
        )
    if "initial_stock" not in columns:
        conn.execute(
            "ALTER TABLE products ADD COLUMN initial_stock INTEGER NOT NULL DEFAULT 0"
        )
        conn.execute("UPDATE products SET initial_stock = stock")


def init_db():
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                price REAL NOT NULL CHECK(price >= 0),
                cost REAL NOT NULL DEFAULT 0 CHECK(cost >= 0),
                stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
                initial_stock INTEGER NOT NULL DEFAULT 0 CHECK(initial_stock >= 0),
                is_deleted INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ახალი',
                payment_status TEXT NOT NULL DEFAULT 'გადაუხდელი',
                total_amount REAL NOT NULL DEFAULT 0,
                delivery_fee REAL NOT NULL DEFAULT 0,
                total_discount REAL NOT NULL DEFAULT 0,
                total_collected REAL NOT NULL DEFAULT 0,
                actual_delivery_cost REAL NOT NULL DEFAULT 0 CHECK(actual_delivery_cost >= 0),
                net_product_revenue REAL NOT NULL DEFAULT 0,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                payment_alert_sent INTEGER NOT NULL DEFAULT 0,
                telegram_alert_sent INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                unit_price REAL NOT NULL,
                unit_cost REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
            """
        )
        _migrate_orders_table(conn)
        _migrate_products_table(conn)


def add_product(name: str, description: str, price: float, cost: float, stock: int) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    stock_value = int(stock)
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO products (
                name, description, price, cost, stock, initial_stock, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, description, price, cost, stock_value, stock_value, now),
        )
        return cursor.lastrowid


def get_all_products():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM products
            WHERE is_deleted = 0
            ORDER BY name COLLATE NOCASE
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_product(product_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE id = ? AND is_deleted = 0",
            (product_id,),
        ).fetchone()
        return dict(row) if row else None


def update_product(
    product_id: int,
    name: str,
    description: str,
    price: float,
    cost: float,
    stock: int,
):
    if not name.strip():
        raise ValueError("გთხოვთ, შეიყვანოთ პროდუქტის სახელი")
    if price < 0:
        raise ValueError("ფასი უარყოფითი ვერ იქნება")
    if cost < 0:
        raise ValueError("თვითღირებულება უარყოფითი ვერ იქნება")
    if stock < 0:
        raise ValueError("მარაგი უარყოფითი ვერ იქნება")

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM products WHERE id = ? AND is_deleted = 0",
            (product_id,),
        ).fetchone()
        if not existing:
            raise ValueError(f"პროდუქტი #{product_id} ვერ მოიძებნა")

        conn.execute(
            """
            UPDATE products
            SET name = ?, description = ?, price = ?, cost = ?, stock = ?
            WHERE id = ? AND is_deleted = 0
            """,
            (name.strip(), description.strip(), price, cost, int(stock), product_id),
        )


def _product_in_active_orders(conn: sqlite3.Connection, product_id: int) -> bool:
    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        WHERE oi.product_id = ?
          AND o.is_deleted = 0
          AND NOT (
              o.payment_status = 'გადახდილი'
              AND o.status IN (?, ?)
          )
        """,
        (product_id, *COMPLETED_ORDER_STATUSES),
    ).fetchone()
    return row["count"] > 0


def delete_product(product_id: int) -> tuple[bool, str]:
    with get_connection() as conn:
        product = conn.execute(
            "SELECT id, name, is_deleted FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
        if not product:
            return False, f"პროდუქტი #{product_id} ვერ მოიძებნა"
        if product["is_deleted"]:
            return False, f"პროდუქტი '{product['name']}' უკვე წაშლილია"

        if _product_in_active_orders(conn, product_id):
            return (
                False,
                "პროდუქტი ვერ წაიშლება, რადგან გამოყენებულია მიმდინარე აქტიურ შეკვეთებში.",
            )

        conn.execute(
            "UPDATE products SET is_deleted = 1 WHERE id = ?",
            (product_id,),
        )
        return True, f"პროდუქტი '{product['name']}' წაიშალა."


def calculate_order_financials(items: list[dict], actual_delivery_cost: float) -> dict:
    """Calculate order totals using the business rules for Samarago sales."""
    base_products_total = sum(
        item["quantity"] * float(item.get("original_price", item["unit_price"]))
        for item in items
    )
    total_collected = sum(item["quantity"] * float(item["unit_price"]) for item in items)
    total_discount = max(0.0, base_products_total - total_collected)
    delivery = max(0.0, float(actual_delivery_cost))
    net_product_revenue = total_collected - delivery

    return {
        "base_products_total": base_products_total,
        "total_collected": total_collected,
        "actual_delivery_cost": delivery,
        "net_product_revenue": net_product_revenue,
        "total_discount": total_discount,
    }


def create_order(
    customer_name: str,
    phone: str,
    address: str,
    items: list[dict],
    actual_delivery_cost: float = 0.0,
) -> int:
    """Create an order and decrease product stock atomically."""
    if not items:
        raise ValueError("შეკვეთა ცარიელია")

    if actual_delivery_cost < 0:
        raise ValueError("კურიერის ხარჯი უარყოფითი ვერ იქნება")

    now = datetime.now().isoformat(timespec="seconds")
    financials = calculate_order_financials(items, actual_delivery_cost)

    with get_connection() as conn:
        for item in items:
            product = conn.execute(
                """
                SELECT id, name, price, cost, stock
                FROM products
                WHERE id = ? AND is_deleted = 0
                """,
                (item["product_id"],),
            ).fetchone()
            if not product:
                raise ValueError(f"პროდუქტი #{item['product_id']} ვერ მოიძებნა")
            if product["stock"] < item["quantity"]:
                raise ValueError(
                    f"'{product['name']}'-ის მარაგი არასაკმარისია "
                    f"(ხელმისაწვდომი: {product['stock']})"
                )

        cursor = conn.execute(
            """
            INSERT INTO orders (
                customer_name, phone, address, status, payment_status,
                total_amount, total_discount,
                total_collected, actual_delivery_cost, net_product_revenue,
                created_at, updated_at
            )
            VALUES (?, ?, ?, 'ახალი', 'გადაუხდელი', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer_name,
                phone,
                address,
                financials["total_collected"],
                financials["total_discount"],
                financials["total_collected"],
                actual_delivery_cost,
                financials["net_product_revenue"],
                now,
                now,
            ),
        )
        order_id = cursor.lastrowid

        for item in items:
            product = conn.execute(
                "SELECT price, cost FROM products WHERE id = ? AND is_deleted = 0",
                (item["product_id"],),
            ).fetchone()
            conn.execute(
                """
                INSERT INTO order_items (order_id, product_id, quantity, unit_price, unit_cost)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    item["product_id"],
                    item["quantity"],
                    item["unit_price"],
                    product["cost"],
                ),
            )
            conn.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (item["quantity"], item["product_id"]),
            )

        return order_id


def _fetch_orders(conn: sqlite3.Connection, is_deleted: int) -> list[dict]:
    orders = conn.execute(
        """
        SELECT * FROM orders
        WHERE is_deleted = ?
        ORDER BY created_at DESC
        """,
        (is_deleted,),
    ).fetchall()
    result = []
    for order in orders:
        order_dict = dict(order)
        items = conn.execute(
            """
            SELECT oi.*, p.name AS product_name
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            WHERE oi.order_id = ?
            """,
            (order["id"],),
        ).fetchall()
        order_dict["items"] = [dict(i) for i in items]
        result.append(order_dict)
    return result


def get_orders():
    """Fetch active (non-deleted) orders."""
    with get_connection() as conn:
        return _fetch_orders(conn, 0)


def get_deleted_orders():
    """Fetch soft-deleted orders for the archive."""
    with get_connection() as conn:
        return _fetch_orders(conn, 1)


def get_all_orders():
    """Backward-compatible alias for active orders."""
    return get_orders()


def get_order_by_id(order_id: int):
    with get_connection() as conn:
        order = conn.execute(
            "SELECT * FROM orders WHERE id = ? AND is_deleted = 0",
            (order_id,),
        ).fetchone()
        if not order:
            return None
        order_dict = dict(order)
        items = conn.execute(
            """
            SELECT oi.*, p.name AS product_name
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            WHERE oi.order_id = ?
            """,
            (order_id,),
        ).fetchall()
        order_dict["items"] = [dict(i) for i in items]
        return order_dict


def update_order_customer_details(
    order_id: int,
    customer_name: str,
    phone: str,
    address: str,
):
    if not customer_name.strip():
        raise ValueError("გთხოვთ, შეიყვანოთ მომხმარებლის სახელი")
    if not phone.strip():
        raise ValueError("გთხოვთ, შეიყვანოთ ტელეფონი")
    if not address.strip():
        raise ValueError("გთხოვთ, შეიყვანოთ მისამართი")

    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        order = conn.execute(
            "SELECT id FROM orders WHERE id = ? AND is_deleted = 0",
            (order_id,),
        ).fetchone()
        if not order:
            raise ValueError(f"შეკვეთა #{order_id} ვერ მოიძებნა")

        conn.execute(
            """
            UPDATE orders
            SET customer_name = ?, phone = ?, address = ?, updated_at = ?
            WHERE id = ? AND is_deleted = 0
            """,
            (customer_name.strip(), phone.strip(), address.strip(), now, order_id),
        )


def update_order_status(order_id: int, status: str):
    if status not in ORDER_STATUSES:
        raise ValueError(f"არასწორი სტატუსი: {status}")

    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        order = conn.execute(
            "SELECT status FROM orders WHERE id = ? AND is_deleted = 0",
            (order_id,),
        ).fetchone()
        if not order:
            raise ValueError(f"შეკვეთა #{order_id} ვერ მოიძებნა")

        old_status = order["status"]
        if old_status != "გაუქმებული" and status == "გაუქმებული":
            _restore_stock(conn, order_id)

        conn.execute(
            "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, order_id),
        )


def update_payment_status(order_id: int, payment_status: str):
    if payment_status not in PAYMENT_STATUSES:
        raise ValueError(f"არასწორი გადახდის სტატუსი: {payment_status}")

    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        updated = conn.execute(
            """
            UPDATE orders
            SET payment_status = ?, updated_at = ?
            WHERE id = ? AND is_deleted = 0
            """,
            (payment_status, now, order_id),
        )
        if updated.rowcount == 0:
            raise ValueError(f"შეკვეთა #{order_id} ვერ მოიძებნა")


def _restore_stock(conn: sqlite3.Connection, order_id: int):
    items = conn.execute(
        "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
        (order_id,),
    ).fetchall()
    for item in items:
        conn.execute(
            "UPDATE products SET stock = stock + ? WHERE id = ?",
            (item["quantity"], item["product_id"]),
        )


def delete_order(order_id: int):
    """Soft-delete an order and restore product stock when applicable."""
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        order = conn.execute(
            "SELECT id, status, is_deleted FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        if not order:
            raise ValueError(f"შეკვეთა #{order_id} ვერ მოიძებნა")
        if order["is_deleted"]:
            raise ValueError(f"შეკვეთა #{order_id} უკვე წაშლილია")

        if order["status"] != "გაუქმებული":
            _restore_stock(conn, order_id)

        conn.execute(
            "UPDATE orders SET is_deleted = 1, updated_at = ? WHERE id = ?",
            (now, order_id),
        )


def get_dashboard_metrics() -> dict:
    with get_connection() as conn:
        sales_row = conn.execute(
            """
            SELECT COALESCE(SUM(
                CASE WHEN total_collected > 0 THEN total_collected ELSE total_amount END
            ), 0) AS total_sales
            FROM orders
            WHERE is_deleted = 0 AND status != 'გაუქმებული'
            """
        ).fetchone()

        profit_row = conn.execute(
            """
            SELECT COALESCE(SUM(
                CASE
                    WHEN o.net_product_revenue > 0 THEN o.net_product_revenue
                    ELSE o.total_amount - COALESCE(o.actual_delivery_cost, o.delivery_fee, 0)
                END
                - (
                    SELECT COALESCE(SUM(oi.unit_cost * oi.quantity), 0)
                    FROM order_items oi
                    WHERE oi.order_id = o.id
                )
            ), 0) AS total_profit
            FROM orders o
            WHERE o.is_deleted = 0 AND o.status != 'გაუქმებული'
            """
        ).fetchone()

        pending_row = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM orders
            WHERE is_deleted = 0 AND status IN ('ახალი', 'გაგზავნილი')
            """
        ).fetchone()

        unpaid_row = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM orders
            WHERE is_deleted = 0
              AND payment_status = 'გადაუხდელი'
              AND status != 'გაუქმებული'
            """
        ).fetchone()

        return {
            "total_sales": sales_row["total_sales"],
            "total_profit": profit_row["total_profit"],
            "pending_orders": pending_row["count"],
            "unpaid_orders": unpaid_row["count"],
        }


UNPAID_ALERT_DAYS = 7


def parse_order_timestamp(value: str) -> datetime:
    """Parse SQLite ISO timestamps stored as TEXT (e.g. 2026-06-23T13:10:15)."""
    normalized = value.strip().replace(" ", "T")
    if normalized.endswith("Z"):
        normalized = normalized[:-1]
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is not None:
        parsed = parsed.replace(tzinfo=None)
    return parsed


def _get_overdue_unpaid_orders(
    alert_sent_column: str,
    alert_days: int = UNPAID_ALERT_DAYS,
) -> list[dict]:
    allowed_columns = {"telegram_alert_sent", "payment_alert_sent"}
    if alert_sent_column not in allowed_columns:
        raise ValueError(f"Unsupported alert column: {alert_sent_column}")

    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT
                id,
                customer_name,
                phone,
                address,
                payment_status,
                created_at,
                total_amount,
                total_collected,
                is_deleted,
                {alert_sent_column}
            FROM orders
            WHERE is_deleted = 0
              AND payment_status = 'გადაუხდელი'
              AND {alert_sent_column} = 0
            ORDER BY created_at ASC
            """
        ).fetchall()

    now = datetime.now()
    threshold = timedelta(days=alert_days)
    overdue = []
    for row in rows:
        order = dict(row)
        try:
            created_at = parse_order_timestamp(order["created_at"])
        except (TypeError, ValueError):
            continue
        if now - created_at > threshold:
            overdue.append(order)
    return overdue


def get_overdue_unpaid_orders(alert_days: int = UNPAID_ALERT_DAYS) -> list[dict]:
    """Return overdue unpaid orders that have not yet received a Telegram alert."""
    return _get_overdue_unpaid_orders("telegram_alert_sent", alert_days)


def get_unacknowledged_payment_alerts(alert_days: int = UNPAID_ALERT_DAYS) -> list[dict]:
    """Return overdue unpaid orders not yet dismissed in the UI."""
    return _get_overdue_unpaid_orders("payment_alert_sent", alert_days)


def update_order_telegram_sent(order_id: int):
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE orders
            SET telegram_alert_sent = 1, updated_at = ?
            WHERE id = ?
              AND is_deleted = 0
              AND telegram_alert_sent = 0
            """,
            (now, order_id),
        )


def acknowledge_payment_alert(order_id: int):
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        updated = conn.execute(
            """
            UPDATE orders
            SET payment_alert_sent = 1, updated_at = ?
            WHERE id = ?
              AND is_deleted = 0
              AND payment_alert_sent = 0
            """,
            (now, order_id),
        )
        if updated.rowcount == 0:
            raise ValueError(f"შეკვეთა #{order_id} ვერ მოიძებნა")
