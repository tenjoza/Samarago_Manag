import os
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

BASE_DIR = Path(__file__).parent

_supabase_client: Client | None = None

ORDER_STATUSES = ("ახალი", "გაგზავნილი", "მიწოდებული", "გაუქმებული")
PAYMENT_STATUSES = ("გადაუხდელი", "გადახდილი")
COMPLETED_ORDER_STATUSES = ("მიწოდებული", "ჩაბარდა")


def get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL", "").strip()
        key = os.getenv("SUPABASE_KEY", "").strip()
        if not url or not key:
            raise ValueError(
                "Supabase credentials are not configured. "
                "Set SUPABASE_URL and SUPABASE_KEY in your .env file."
            )
        _supabase_client = create_client(url, key)
    return _supabase_client


def _rows(response) -> list[dict]:
    return list(response.data or [])


def _first(response) -> dict | None:
    rows = _rows(response)
    return rows[0] if rows else None


def _order_net_revenue(order: dict) -> float:
    net = float(order.get("net_product_revenue") or 0)
    if net > 0:
        return net
    delivery = order.get("actual_delivery_cost")
    if delivery in (None, ""):
        delivery = order.get("delivery_fee") or 0
    return float(order.get("total_amount") or 0) - float(delivery or 0)


def _is_active_order(order: dict) -> bool:
    if order.get("is_deleted"):
        return False
    if order.get("status") == "გაუქმებული":
        return False
    if (
        order.get("payment_status") == "გადახდილი"
        and order.get("status") in COMPLETED_ORDER_STATUSES
    ):
        return False
    return True


def _is_completed_order(order: dict) -> bool:
    return (
        not order.get("is_deleted")
        and order.get("payment_status") == "გადახდილი"
        and order.get("status") in COMPLETED_ORDER_STATUSES
    )


def _order_items_profit(order_items: list[dict]) -> float:
    return sum(
        (float(item.get("unit_price") or 0) - float(item.get("unit_cost") or 0))
        * int(item.get("quantity") or 0)
        for item in order_items
    )


def _normalize_order_items(order: dict) -> dict:
    items = order.pop("order_items", None) or []
    normalized: list[dict] = []
    for item in items:
        row = dict(item)
        product = row.pop("products", None) or {}
        row["product_name"] = product.get("name", "")
        normalized.append(row)
    order["items"] = normalized
    return order


def _attach_order_items(orders: list[dict]) -> list[dict]:
    """Legacy batch loader — prefer nested select in _fetch_orders when possible."""
    if not orders:
        return []

    order_ids = [order["id"] for order in orders]
    items = _rows(
        get_supabase()
        .table("order_items")
        .select("*, products(name)")
        .in_("order_id", order_ids)
        .execute()
    )

    items_by_order: dict[int, list[dict]] = {}
    for item in items:
        product = item.pop("products", None) or {}
        item["product_name"] = product.get("name", "")
        items_by_order.setdefault(item["order_id"], []).append(item)

    for order in orders:
        order["items"] = items_by_order.get(order["id"], [])
    return orders


def _get_order_item_rows(order_id: int) -> list[dict]:
    return _rows(
        get_supabase()
        .table("order_items")
        .select("*")
        .eq("order_id", order_id)
        .execute()
    )


def init_db():
    """Ensure Supabase fallback delivery rates exist when the table is empty."""
    init_delivery_rates()


# (location, max_weight_kg, price_gel)
DELIVERY_LOCATIONS = [
    "თბილისი",
    "თბილისის შემოგარენი",
    "რუსთავი",
    "სხვა ქალაქი",
    "სოფელი",
    "მაღალ მთ. რეგიონი",
    "მაღალ მთ. სოფელი",
]

_DEFAULT_DELIVERY_RATES: list[tuple[str, float, float]] = [
    ("თბილისი", 1, 5),
    ("თბილისი", 3, 7),
    ("თბილისი", 5, 10),
    ("თბილისი", 10, 15),
    ("თბილისი", 20, 25),
    ("თბილისის შემოგარენი", 1, 6),
    ("თბილისის შემოგარენი", 3, 8),
    ("თბილისის შემოგარენი", 5, 12),
    ("თბილისის შემოგარენი", 10, 18),
    ("თბილისის შემოგარენი", 20, 28),
    ("რუსთავი", 1, 5),
    ("რუსთავი", 3, 7),
    ("რუსთავი", 5, 10),
    ("რუსთავი", 10, 15),
    ("რუსთავი", 20, 25),
    ("სხვა ქალაქი", 1, 8),
    ("სხვა ქალაქი", 3, 11),
    ("სხვა ქალაქი", 5, 15),
    ("სხვა ქალაქი", 10, 20),
    ("სხვა ქალაქი", 20, 30),
    ("სოფელი", 1, 10),
    ("სოფელი", 3, 14),
    ("სოფელი", 5, 18),
    ("სოფელი", 10, 25),
    ("სოფელი", 20, 35),
    ("მაღალ მთ. რეგიონი", 1, 12),
    ("მაღალ მთ. რეგიონი", 3, 16),
    ("მაღალ მთ. რეგიონი", 5, 22),
    ("მაღალ მთ. რეგიონი", 10, 30),
    ("მაღალ მთ. რეგიონი", 20, 40),
    ("მაღალ მთ. სოფელი", 1, 14),
    ("მაღალ მთ. სოფელი", 3, 18),
    ("მაღალ მთ. სოფელი", 5, 25),
    ("მაღალ მთ. სოფელი", 10, 35),
    ("მაღალ მთ. სოფელი", 20, 45),
]


def init_delivery_rates() -> None:
    """Seed delivery_rates in Supabase only when the table is empty."""
    existing_rows = _rows(
        get_supabase().table("delivery_rates").select("id").limit(1).execute()
    )
    if existing_rows:
        return

    get_supabase().table("delivery_rates").insert(
        [
            {"city": city, "weight_limit": weight_limit, "price": price}
            for city, weight_limit, price in _DEFAULT_DELIVERY_RATES
        ]
    ).execute()


def get_delivery_locations() -> list[str]:
    rows = _rows(
        get_supabase().table("delivery_rates").select("city").order("city").execute()
    )
    locations = sorted({row["city"] for row in rows if row.get("city")})
    return locations or list(DELIVERY_LOCATIONS)


def get_delivery_cities() -> list[str]:
    """Backward-compatible alias for delivery location labels."""
    return get_delivery_locations()


def get_delivery_price(location: str, weight: float) -> float:
    """Return delivery price for a location and package weight (kg) from Supabase."""
    if not location.strip():
        raise ValueError("გთხოვთ, აირჩიოთ მიწოდების ადგილი")
    if weight < 0:
        raise ValueError("წონა უარყოფითი ვერ იქნება")

    effective_weight = max(float(weight), 0.001)
    row = _first(
        get_supabase()
        .table("delivery_rates")
        .select("price")
        .eq("city", location.strip())
        .gte("weight_limit", effective_weight)
        .order("weight_limit")
        .limit(1)
        .execute()
    )
    if row:
        return float(row["price"])

    row = _first(
        get_supabase()
        .table("delivery_rates")
        .select("price")
        .eq("city", location.strip())
        .order("weight_limit", desc=True)
        .limit(1)
        .execute()
    )
    if row:
        return float(row["price"])

    raise ValueError(f"მიწოდების ტარიფი ვერ მოიძებნა ადგილისთვის: {location}")


def add_product(
    name: str,
    description: str,
    price: float,
    cost: float,
    stock: int,
    weight: float = 0.0,
) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    stock_value = int(stock)
    row = _first(
        get_supabase()
        .table("products")
        .insert(
            {
                "name": name,
                "description": description,
                "price": price,
                "cost": cost,
                "weight": float(weight),
                "stock": stock_value,
                "initial_stock": stock_value,
                "is_deleted": 0,
                "created_at": now,
            }
        )
        .execute()
    )
    if not row:
        raise RuntimeError("პროდუქტის შენახვა ვერ მოხერხდა")
    product_id = int(row["id"])
    return product_id


def get_all_products():
    return _rows(
        get_supabase()
        .table("products")
        .select("*")
        .eq("is_deleted", 0)
        .order("name")
        .execute()
    )


def get_product(product_id: int):
    return _first(
        get_supabase()
        .table("products")
        .select("*")
        .eq("id", product_id)
        .eq("is_deleted", 0)
        .execute()
    )


def update_product(
    product_id: int,
    name: str,
    description: str,
    price: float,
    cost: float,
    stock: int,
    weight: float = 0.0,
):
    if not name.strip():
        raise ValueError("გთხოვთ, შეიყვანოთ პროდუქტის სახელი")
    if price < 0:
        raise ValueError("ფასი უარყოფითი ვერ იქნება")
    if cost < 0:
        raise ValueError("თვითღირებულება უარყოფითი ვერ იქნება")
    if weight < 0:
        raise ValueError("წონა უარყოფითი ვერ იქნება")
    if stock < 0:
        raise ValueError("მარაგი უარყოფითი ვერ იქნება")

    existing = get_product(product_id)
    if not existing:
        raise ValueError(f"პროდუქტი #{product_id} ვერ მოიძებნა")

    get_supabase().table("products").update(
        {
            "name": name.strip(),
            "description": description.strip(),
            "price": price,
            "cost": cost,
            "weight": float(weight),
            "stock": int(stock),
        }
    ).eq("id", product_id).eq("is_deleted", 0).execute()


def _product_in_active_orders(product_id: int) -> bool:
    items = _rows(
        get_supabase()
        .table("order_items")
        .select("order_id")
        .eq("product_id", product_id)
        .execute()
    )
    if not items:
        return False

    order_ids = list({item["order_id"] for item in items})
    orders = _rows(
        get_supabase()
        .table("orders")
        .select("id, status, payment_status, is_deleted")
        .in_("id", order_ids)
        .execute()
    )
    for order in orders:
        if order.get("is_deleted"):
            continue
        if (
            order.get("payment_status") == "გადახდილი"
            and order.get("status") in COMPLETED_ORDER_STATUSES
        ):
            continue
        return True
    return False


def delete_product(product_id: int) -> tuple[bool, str]:
    product = _first(
        get_supabase().table("products").select("id, name, is_deleted").eq("id", product_id).execute()
    )
    if not product:
        return False, f"პროდუქტი #{product_id} ვერ მოიძებნა"
    if product["is_deleted"]:
        return False, f"პროდუქტი '{product['name']}' უკვე წაშლილია"

    if _product_in_active_orders(product_id):
        return (
            False,
            "პროდუქტი ვერ წაიშლება, რადგან გამოყენებულია მიმდინარე აქტიურ შეკვეთებში.",
        )

    get_supabase().table("products").update({"is_deleted": 1}).eq("id", product_id).execute()
    return True, f"პროდუქტი '{product['name']}' წაიშალა."


def calculate_order_financials(items: list[dict], delivery_cost: float) -> dict:
    """Calculate order totals using the business rules for Samarago sales."""
    base_products_total = sum(
        item["quantity"] * float(item.get("original_price", item["unit_price"]))
        for item in items
    )
    products_collected = sum(
        item["quantity"] * float(item["unit_price"]) for item in items
    )
    total_discount = max(0.0, base_products_total - products_collected)
    delivery = max(0.0, float(delivery_cost))
    total_collected = products_collected + delivery
    net_product_revenue = products_collected - delivery

    return {
        "base_products_total": base_products_total,
        "products_collected": products_collected,
        "total_collected": total_collected,
        "delivery_fee": delivery,
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
    """Create an order and decrease product stock."""
    if not items:
        raise ValueError("შეკვეთა ცარიელია")

    if actual_delivery_cost < 0:
        raise ValueError("კურიერის ხარჯი უარყოფითი ვერ იქნება")

    now = datetime.now().isoformat(timespec="seconds")
    financials = calculate_order_financials(items, actual_delivery_cost)
    product_cache: dict[int, dict] = {}

    for item in items:
        product = get_product(item["product_id"])
        if not product:
            raise ValueError(f"პროდუქტი #{item['product_id']} ვერ მოიძებნა")
        if product["stock"] < item["quantity"]:
            raise ValueError(
                f"'{product['name']}'-ის მარაგი არასაკმარისია "
                f"(ხელმისაწვდომი: {product['stock']})"
            )
        product_cache[product["id"]] = product

    order_row = _first(
        get_supabase()
        .table("orders")
        .insert(
            {
                "customer_name": customer_name,
                "phone": phone,
                "address": address,
                "status": "ახალი",
                "payment_status": "გადაუხდელი",
                "total_amount": financials["total_collected"],
                "delivery_fee": financials["delivery_fee"],
                "total_discount": financials["total_discount"],
                "total_collected": financials["total_collected"],
                "actual_delivery_cost": financials["actual_delivery_cost"],
                "net_product_revenue": financials["net_product_revenue"],
                "shipping_charged": 0,
                "is_deleted": 0,
                "payment_alert_sent": 0,
                "telegram_alert_sent": 0,
                "created_at": now,
                "updated_at": now,
            }
        )
        .execute()
    )
    if not order_row:
        raise RuntimeError("შეკვეთის შენახვა ვერ მოხერხდა")

    order_id = int(order_row["id"])

    for item in items:
        product = product_cache[item["product_id"]]
        item_row = _first(
            get_supabase()
            .table("order_items")
            .insert(
                {
                    "order_id": order_id,
                    "product_id": item["product_id"],
                    "quantity": item["quantity"],
                    "unit_price": item["unit_price"],
                    "unit_cost": product["cost"],
                }
            )
            .execute()
        )
        if not item_row:
            raise RuntimeError("შეკვეთის პოზიციის შენახვა ვერ მოხერხდა")

        new_stock = int(product["stock"]) - int(item["quantity"])
        get_supabase().table("products").update({"stock": new_stock}).eq(
            "id", item["product_id"]
        ).execute()
        product["stock"] = new_stock

    return order_id


def _fetch_orders(is_deleted: int | None = None) -> list[dict]:
    query = (
        get_supabase()
        .table("orders")
        .select("*, order_items(*, products(name))")
        .order("created_at", desc=True)
    )
    if is_deleted is not None:
        query = query.eq("is_deleted", is_deleted)
    orders = _rows(query.execute())
    return [_normalize_order_items(order) for order in orders]


def get_orders():
    """Fetch active (non-deleted) orders."""
    return _fetch_orders(0)


def get_deleted_orders():
    """Fetch soft-deleted orders for the archive."""
    return _fetch_orders(1)


def get_all_orders_with_items():
    """Fetch active and deleted orders with items in one request."""
    return _fetch_orders()


def get_orders_for_period(
    period_start: datetime,
    period_end: datetime,
) -> list[dict]:
    start_iso = period_start.isoformat(timespec="seconds")
    end_iso = period_end.isoformat(timespec="seconds")
    orders = _rows(
        get_supabase()
        .table("orders")
        .select("*, order_items(*, products(name))")
        .eq("is_deleted", 0)
        .gte("created_at", start_iso)
        .lt("created_at", end_iso)
        .order("created_at", desc=True)
        .execute()
    )
    return [_normalize_order_items(order) for order in orders]


def get_all_orders():
    """Backward-compatible alias for active orders."""
    return get_orders()


def get_order_by_id(order_id: int):
    order = _first(
        get_supabase()
        .table("orders")
        .select("*, order_items(*, products(name))")
        .eq("id", order_id)
        .eq("is_deleted", 0)
        .execute()
    )
    if not order:
        return None
    return _normalize_order_items(order)


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
    updated = _rows(
        get_supabase()
        .table("orders")
        .update(
            {
                "customer_name": customer_name.strip(),
                "phone": phone.strip(),
                "address": address.strip(),
                "updated_at": now,
            }
        )
        .eq("id", order_id)
        .eq("is_deleted", 0)
        .execute()
    )
    if not updated:
        raise ValueError(f"შეკვეთა #{order_id} ვერ მოიძებნა")


def update_order_status(order_id: int, status: str):
    if status not in ORDER_STATUSES:
        raise ValueError(f"არასწორი სტატუსი: {status}")

    now = datetime.now().isoformat(timespec="seconds")
    order = _first(
        get_supabase()
        .table("orders")
        .select("status")
        .eq("id", order_id)
        .eq("is_deleted", 0)
        .execute()
    )
    if not order:
        raise ValueError(f"შეკვეთა #{order_id} ვერ მოიძებნა")

    old_status = order["status"]
    if old_status != "გაუქმებული" and status == "გაუქმებული":
        _restore_stock(order_id)

    get_supabase().table("orders").update(
        {"status": status, "updated_at": now}
    ).eq("id", order_id).execute()


def update_payment_status(order_id: int, payment_status: str):
    if payment_status not in PAYMENT_STATUSES:
        raise ValueError(f"არასწორი გადახდის სტატუსი: {payment_status}")

    now = datetime.now().isoformat(timespec="seconds")
    updated = _rows(
        get_supabase()
        .table("orders")
        .update({"payment_status": payment_status, "updated_at": now})
        .eq("id", order_id)
        .eq("is_deleted", 0)
        .execute()
    )
    if not updated:
        raise ValueError(f"შეკვეთა #{order_id} ვერ მოიძებნა")


def _restore_stock(order_id: int):
    items = _get_order_item_rows(order_id)
    for item in items:
        product = _first(
            get_supabase()
            .table("products")
            .select("stock")
            .eq("id", item["product_id"])
            .execute()
        )
        if not product:
            continue
        get_supabase().table("products").update(
            {"stock": int(product["stock"]) + int(item["quantity"])}
        ).eq("id", item["product_id"]).execute()


def delete_order(order_id: int):
    """Soft-delete an order and restore product stock when applicable."""
    now = datetime.now().isoformat(timespec="seconds")

    order = _first(
        get_supabase()
        .table("orders")
        .select("id, status, is_deleted")
        .eq("id", order_id)
        .execute()
    )
    if not order:
        raise ValueError(f"შეკვეთა #{order_id} ვერ მოიძებნა")
    if order["is_deleted"]:
        raise ValueError(f"შეკვეთა #{order_id} უკვე წაშლილია")

    if order["status"] != "გაუქმებული":
        _restore_stock(order_id)

    get_supabase().table("orders").update(
        {"is_deleted": 1, "updated_at": now}
    ).eq("id", order_id).execute()


def get_dashboard_period_bounds(
    period: str,
    *,
    month: int | None = None,
    year: int | None = None,
) -> tuple[datetime, datetime]:
    """Return [start, end) bounds for dashboard period filters."""
    now = datetime.now()
    if year is None:
        year = now.year

    if period == "კვირა":
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = start + timedelta(days=7)
    elif period == "თვე":
        selected_month = month or now.month
        start = datetime(year, selected_month, 1)
        if selected_month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, selected_month + 1, 1)
    elif period == "წელი":
        start = datetime(year, 1, 1)
        end = datetime(year + 1, 1, 1)
    else:
        raise ValueError(f"Unknown dashboard period: {period}")

    return start, end


def filter_orders_by_period(
    orders: list[dict],
    period_start: datetime,
    period_end: datetime,
) -> list[dict]:
    filtered = []
    for order in orders:
        created_at = parse_order_timestamp(order["created_at"])
        if period_start <= created_at < period_end:
            filtered.append(order)
    return filtered


def get_dashboard_metrics(
    period_start: datetime,
    period_end: datetime,
) -> dict:
    start_iso = period_start.isoformat(timespec="seconds")
    end_iso = period_end.isoformat(timespec="seconds")

    orders = _rows(
        get_supabase()
        .table("orders")
        .select("*, order_items(quantity, unit_cost, unit_price)")
        .gte("created_at", start_iso)
        .lt("created_at", end_iso)
        .execute()
    )

    paid_revenue = 0.0
    pending_revenue = 0.0
    total_profit = 0.0
    pending_orders = 0
    unpaid_orders = 0

    for order in orders:
        if order.get("is_deleted"):
            continue

        net_revenue = _order_net_revenue(order)
        order_items = order.pop("order_items", None) or []

        if _is_completed_order(order):
            total_profit += _order_items_profit(order_items)

        if order.get("status") in ("ახალი", "გაგზავნილი"):
            pending_orders += 1

        if (
            order.get("payment_status") == "გადაუხდელი"
            and order.get("status") != "გაუქმებული"
        ):
            unpaid_orders += 1

        if order.get("status") == "გაუქმებული":
            continue

        if order.get("payment_status") == "გადახდილი":
            paid_revenue += net_revenue
        elif _is_active_order(order):
            pending_revenue += net_revenue

    return {
        "paid_revenue": paid_revenue,
        "pending_revenue": pending_revenue,
        "total_profit": total_profit,
        "pending_orders": pending_orders,
        "unpaid_orders": unpaid_orders,
    }


UNPAID_ALERT_DAYS = 7


def parse_order_timestamp(value: str) -> datetime:
    """Parse ISO timestamps stored as TEXT (e.g. 2026-06-23T13:10:15)."""
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

    rows = _rows(
        get_supabase()
        .table("orders")
        .select(
            "id, customer_name, phone, address, payment_status, created_at, "
            "total_amount, total_collected, is_deleted, "
            f"{alert_sent_column}"
        )
        .eq("is_deleted", 0)
        .eq("payment_status", "გადაუხდელი")
        .eq(alert_sent_column, 0)
        .order("created_at")
        .execute()
    )

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
    get_supabase().table("orders").update(
        {"telegram_alert_sent": 1, "updated_at": now}
    ).eq("id", order_id).eq("is_deleted", 0).eq("telegram_alert_sent", 0).execute()


def acknowledge_payment_alert(order_id: int):
    now = datetime.now().isoformat(timespec="seconds")
    updated = _rows(
        get_supabase()
        .table("orders")
        .update({"payment_alert_sent": 1, "updated_at": now})
        .eq("id", order_id)
        .eq("is_deleted", 0)
        .eq("payment_alert_sent", 0)
        .execute()
    )
    if not updated:
        raise ValueError(f"შეკვეთა #{order_id} ვერ მოიძებნა")
