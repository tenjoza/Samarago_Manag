import importlib
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

import database as db

importlib.reload(db)

# Telegram configuration
TELEGRAM_TOKEN = "8588275896:AAEOjGH75LGN_LpYHfOZ-bSRo4ZS78V1dts"
CHAT_ID = "-5525866790"

LOGO_PATH = Path(__file__).parent / "logo.png"

st.set_page_config(
    page_title="Samarago გაყიდვები",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Georgian:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans Georgian', sans-serif; }
    .block-container { padding-top: 2rem; max-width: 1200px; }
    div[data-testid="stTabs"] button { font-weight: 600; font-size: 0.95rem; }
    div[data-testid="stRadio"] > div {
        gap: 0.5rem;
        margin-bottom: 1rem;
    }
    div[data-testid="stRadio"] label {
        background: #f1f5f9;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.45rem 1rem;
        font-weight: 600;
    }
    div[data-testid="stRadio"] label:hover {
        background: #e2e8f0;
    }
    .brand-title {
        font-size: 1.75rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0;
        line-height: 1.2;
    }
    .brand-subtitle {
        font-size: 1rem;
        font-weight: 600;
        color: #334155;
        margin: 0.15rem 0 0.35rem 0;
    }
    .brand-caption {
        font-size: 0.9rem;
        color: #64748b;
        margin: 0;
    }
</style>
"""

db.init_db()

TAB_OPTIONS = ["დაფა", "პროდუქტები", "შეკვეთები"]
TAB_LABELS = {
    "დაფა": "📊 დაფა",
    "პროდუქტები": "📦 პროდუქტები",
    "შეკვეთები": "🛒 შეკვეთები",
}

ORDER_STATUS_COLORS = {
    "ახალი": ("#fef08a", "#854d0e"),
    "გაგზავნილი": ("#bfdbfe", "#1e40af"),
    "მიწოდებული": ("#bbf7d0", "#166534"),
    "ჩაბარდა": ("#bbf7d0", "#166534"),
    "გაუქმებული": ("#fecaca", "#b91c1c"),
}

PAYMENT_STATUS_COLORS = {
    "გადახდილი": ("#bbf7d0", "#166534"),
    "გადაუხდელი": ("#fecaca", "#b91c1c"),
}

ORDER_BADGE_COLOR = {
    "ახალი": "yellow",
    "გაგზავნილი": "blue",
    "მიწოდებული": "green",
    "ჩაბარდა": "green",
    "გაუქმებული": "red",
}

PAYMENT_BADGE_COLOR = {
    "გადახდილი": "green",
    "გადაუხდელი": "red",
}


def format_currency(amount: float) -> str:
    return f"₾{amount:,.2f}"


def format_order_id(order_id: int) -> str:
    return f"{order_id:05d}"


def send_telegram_message(message: str) -> bool:
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        response = requests.post(
            url,
            json={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
        return response.ok
    except requests.RequestException:
        return False


def _display_field(value) -> str:
    if value is None:
        return "N/A"
    text = str(value).strip()
    return text if text else "N/A"


def format_overdue_telegram_message(order: dict) -> str:
    order_id = int(order["id"])
    total = order_collected_amount(order)
    return (
        f"⚠️ <b>ვადაგადაცილებული შეკვეთა:</b> #{format_order_id(order_id)}\n"
        f"👤 <b>კლიენტი:</b> {_display_field(order.get('customer_name'))}\n"
        f"📞 <b>ტელეფონი:</b> {_display_field(order.get('phone'))}\n"
        f"🏠 <b>მისამართი:</b> {_display_field(order.get('address'))}\n"
        f"💰 <b>გადასახდელი თანხა:</b> {total:,.2f} ₾"
    )


def order_collected_amount(order: dict) -> float:
    if order.get("total_collected"):
        return float(order["total_collected"])
    return float(order.get("total_amount") or 0)


def show_status_badge(status: str):
    st.badge(status, color=ORDER_BADGE_COLOR.get(status, "gray"))


def show_payment_badge(payment_status: str):
    st.badge(payment_status, color=PAYMENT_BADGE_COLOR.get(payment_status, "gray"))


def _cell_style(label: str, colors: dict[str, tuple[str, str]]) -> str:
    bg, fg = colors.get(label, ("#f1f5f9", "#475569"))
    return f"background-color: {bg}; color: {fg}; font-weight: 600;"


OVERDUE_DATE_CELL_STYLE = "background-color: #ffcccc; color: #b91c1c; font-weight: 600;"


def _is_overdue_unpaid_row(row: pd.Series) -> bool:
    if row.get("გადახდა") != "გადაუხდელი":
        return False

    date_str = row.get("თარიღი")
    if not date_str:
        return False

    try:
        created_at = db.parse_order_timestamp(f"{str(date_str)[:10]}T00:00:00")
    except (TypeError, ValueError):
        return False

    return datetime.now() - created_at > timedelta(days=db.UNPAID_ALERT_DAYS)


def _highlight_overdue_date_row(row: pd.Series) -> list[str]:
    if not _is_overdue_unpaid_row(row):
        return [""] * len(row)
    return [
        OVERDUE_DATE_CELL_STYLE if col == "თარიღი" else ""
        for col in row.index
    ]


def style_orders_dataframe(df: pd.DataFrame):
    styled = df.style
    if "სტატუსი" in df.columns:
        styled = styled.map(
            lambda val: _cell_style(str(val), ORDER_STATUS_COLORS),
            subset=["სტატუსი"],
        )
    if "გადახდა" in df.columns:
        styled = styled.map(
            lambda val: _cell_style(str(val), PAYMENT_STATUS_COLORS),
            subset=["გადახდა"],
        )
    return styled


def style_active_orders_dataframe(df: pd.DataFrame):
    styled = style_orders_dataframe(df)
    if "თარიღი" in df.columns:
        styled = styled.apply(_highlight_overdue_date_row, axis=1)
    return styled


def build_orders_rows(orders: list[dict]) -> list[dict]:
    rows = []
    for o in orders:
        product_names = ", ".join(
            f"{i['product_name']} ×{i['quantity']}" for i in o["items"]
        )
        rows.append(
            {
                "№": format_order_id(o["id"]),
                "მომხმარებელი": o["customer_name"],
                "პროდუქტები": product_names,
                "თანხა": format_currency(order_collected_amount(o)),
                "Net Revenue": format_currency(o.get("net_product_revenue") or 0),
                "სტატუსი": o["status"],
                "გადახდა": o["payment_status"],
                "თარიღი": o["created_at"][:10],
            }
        )
    return rows


def calc_cart_totals(cart_items: list[dict], actual_delivery_cost: float) -> dict:
    if not hasattr(db, "calculate_order_financials"):
        raise AttributeError(
            "database.calculate_order_financials არ მოიძებნა. გადატვირთეთ აპლიკაცია."
        )
    return db.calculate_order_financials(cart_items, actual_delivery_cost)


def _summary_row(label: str, value: str):
    left, right = st.columns([3, 1])
    with left:
        st.write(label)
    with right:
        st.write(value)


def render_order_summary(totals: dict):
    st.subheader("შეკვეთის შეჯამება")
    with st.container(border=True):
        if totals["total_discount"] > 0:
            _summary_row(
                "პროდუქტების ბაზის ფასის ჯამი",
                format_currency(totals["base_products_total"]),
            )
            _summary_row(
                "გაკეთებული ფასდაკლება",
                f"-{format_currency(totals['total_discount'])}",
            )

        _summary_row(
            "კლიენტის გადასახდელი ჯამი",
            format_currency(totals["total_collected"]),
        )
        _summary_row(
            "კურიერის რეალური ხარჯი",
            f"-{format_currency(totals['actual_delivery_cost'])}",
        )
        st.divider()
        st.metric(
            label="პროდუქტის რეალური გასაყიდი ფასი (Net Revenue)",
            value=format_currency(totals["net_product_revenue"]),
        )


def render_order_card_header(order: dict, collected: float):
    title_col, status_col, payment_col = st.columns([4, 1, 1])
    with title_col:
        st.markdown(
            f"**შეკვეთა #{format_order_id(order['id'])}** · {order['customer_name']} · "
            f"{format_currency(collected)}"
        )
    with status_col:
        show_status_badge(order["status"])
    with payment_col:
        show_payment_badge(order["payment_status"])


@st.dialog("წაშლის დადასტურება")
def confirm_delete_product_dialog(product_id: int):
    product = db.get_product(product_id)
    if not product:
        st.error("პროდუქტი ვერ მოიძებნა")
        if st.button("დახურვა"):
            _clear_product_action_state()
            st.rerun()
        return

    st.warning("დარწმუნებული ხართ, რომ გსურთ პროდუქტის წაშლა?")
    st.caption(f"პროდუქტი: {product['name']}")

    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("დიახ", type="primary", use_container_width=True, key=f"del_yes_{product_id}"):
            success, message = db.delete_product(product_id)
            if success:
                _clear_product_action_state()
                st.toast(message, icon="✅")
                st.rerun()
            elif "აქტიურ შეკვეთებში" in message:
                st.toast(
                    "⚠️ პროდუქტი ვერ წაიშლება, რადგან გამოყენებულია მიმდინარე აქტიურ შეკვეთებში.",
                    icon="🚫",
                )
                st.warning(message)
            else:
                st.warning(message)
    with col_no:
        if st.button("არა", use_container_width=True, key=f"del_no_{product_id}"):
            _clear_product_action_state()
            st.rerun()


@st.dialog("პროდუქტის რედაქტირება")
def edit_product_dialog(product_id: int):
    product = db.get_product(product_id)
    if not product:
        st.error("პროდუქტი ვერ მოიძებნა")
        if st.button("დახურვა"):
            _clear_product_action_state()
            st.rerun()
        return

    pending = st.session_state.get("product_edit_pending")

    if pending and pending.get("product_id") == product_id:
        st.warning("დარწმუნებული ხართ, რომ გსურთ ცვლილებების შენახვა?")
        st.caption(
            f"{pending['name']} · {format_currency(pending['price'])} · მარაგი: {pending['stock']}"
        )
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button(
                "დიახ, შენახვა",
                type="primary",
                use_container_width=True,
                key=f"edit_yes_{product_id}",
            ):
                try:
                    db.update_product(
                        product_id,
                        pending["name"],
                        product["description"],
                        pending["price"],
                        product["cost"],
                        pending["stock"],
                    )
                    _clear_product_action_state()
                    st.session_state.pop("product_edit_pending", None)
                    st.success("პროდუქტი განახლდა!")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
        with col_no:
            if st.button("არა", use_container_width=True, key=f"edit_no_{product_id}"):
                st.session_state.pop("product_edit_pending", None)
                st.rerun()
        return

    with st.form("edit_product_form"):
        edit_name = st.text_input("სახელი *", value=product["name"])
        edit_price = st.number_input(
            "გასაყიდი ფასი (₾) *",
            min_value=0.0,
            step=0.5,
            format="%.2f",
            value=float(product["price"]),
        )
        edit_stock = st.number_input(
            "მარაგი *",
            min_value=0,
            step=1,
            value=int(product["stock"]),
        )

        if st.form_submit_button("შენახვა", type="primary", use_container_width=True):
            if not edit_name.strip():
                st.error("გთხოვთ, შეიყვანოთ პროდუქტის სახელი.")
            else:
                st.session_state.product_edit_pending = {
                    "product_id": product_id,
                    "name": edit_name.strip(),
                    "price": float(edit_price),
                    "stock": int(edit_stock),
                }
                st.rerun()


def _clear_product_action_state():
    st.session_state.pop("product_action", None)
    st.session_state.pop("product_action_id", None)
    st.session_state.pop("product_edit_pending", None)


def _dismiss_new_product_dialog():
    st.session_state.show_new_product_dialog = False


PRODUCTS_TABLE_KEY = "products_table"
LOW_STOCK_THRESHOLD = 10


@st.dialog("ახალი პროდუქტის დამატება", on_dismiss=_dismiss_new_product_dialog)
def add_new_product_dialog():
    with st.form("add_product_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("სახელი *", placeholder="მაგ: ბამბის პერანგი")
            price = st.number_input("გასაყიდი ფასი (₾) *", min_value=0.0, step=0.5, format="%.2f")
            stock = st.number_input("მარაგი *", min_value=0, step=1)
        with col2:
            description = st.text_area("აღწერა", placeholder="ფერი, ზომა, მასალა...")
            cost = st.number_input("თვითღირებულება (₾)", min_value=0.0, step=0.5, format="%.2f")

        submitted = st.form_submit_button(
            "პროდუქტის დამატება", type="primary", use_container_width=True
        )
        if submitted:
            if not name.strip():
                st.error("გთხოვთ, შეიყვანოთ პროდუქტის სახელი.")
            else:
                db.add_product(name.strip(), description.strip(), price, cost, int(stock))
                _dismiss_new_product_dialog()
                st.toast(f"პროდუქტი '{name.strip()}' წარმატებით დაემატა!", icon="✅")
                st.rerun()


def _low_stock_style(value) -> str:
    if isinstance(value, (int, float)) and value < LOW_STOCK_THRESHOLD:
        return "background-color: #fecaca; color: #b91c1c; font-weight: 600;"
    return ""


PRODUCT_PRICE_COLUMNS = ("ფასი (₾)", "თვითღირებულება (₾)")


def style_products_dataframe(df: pd.DataFrame):
    styled = df.style
    price_cols = [col for col in PRODUCT_PRICE_COLUMNS if col in df.columns]
    if price_cols:
        styled = styled.format("{:.2f}", subset=price_cols)
    if "ნაშთი" in df.columns:
        styled = styled.map(_low_stock_style, subset=["ნაშთი"])
    return styled


def build_products_df(products: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "სახელი": p["name"],
                "აღწერა": p["description"],
                "ფასი (₾)": p["price"],
                "თვითღირებულება (₾)": p["cost"],
                "ნაშთი": p["stock"],
                "რაოდენობა": p.get("initial_stock", p["stock"]),
                "დამატების თარიღი": (p.get("created_at") or "")[:10],
            }
            for p in products
        ]
    )


def get_selected_product_id(products: list[dict]) -> int | None:
    state = st.session_state.get(PRODUCTS_TABLE_KEY)
    if state is None:
        return None

    selection = getattr(state, "selection", None)
    if selection is None:
        return None

    rows = getattr(selection, "rows", None)
    if not rows:
        return None

    row_idx = rows[0]
    if row_idx < 0 or row_idx >= len(products):
        return None

    return int(products[row_idx]["id"])


def _clear_order_action_state():
    st.session_state.pop("order_action", None)
    st.session_state.pop("order_action_id", None)
    st.session_state.pop("order_edit_pending", None)


@st.dialog("შეკვეთის წაშლა")
def confirm_delete_order_dialog(order_id: int):
    order = db.get_order_by_id(order_id)
    if not order:
        st.error("შეკვეთა ვერ მოიძებნა")
        if st.button("დახურვა", key=f"order_del_close_{order_id}"):
            _clear_order_action_state()
            st.rerun()
        return

    st.warning(
        "დარწმუნებული ხართ, რომ გსურთ ამ შეკვეთის წაშლა? "
        "(პროდუქტის მარაგი ავტომატურად დაბრუნდება საწყობში)"
    )
    st.caption(
        f"შეკვეთა #{format_order_id(order['id'])} · {order['customer_name']} · "
        f"{format_currency(order_collected_amount(order))}"
    )

    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("დიახ", type="primary", use_container_width=True, key=f"order_del_yes_{order_id}"):
            try:
                db.delete_order(order_id)
                _clear_order_action_state()
                st.success(f"შეკვეთა #{format_order_id(order_id)} არქივში გადავიდა.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
    with col_no:
        if st.button("არა", use_container_width=True, key=f"order_del_no_{order_id}"):
            _clear_order_action_state()
            st.rerun()


@st.dialog("მომხმარებლის რედაქტირება")
def edit_order_customer_dialog(order_id: int):
    order = db.get_order_by_id(order_id)
    if not order:
        st.error("შეკვეთა ვერ მოიძებნა")
        if st.button("დახურვა", key=f"order_edit_close_{order_id}"):
            _clear_order_action_state()
            st.rerun()
        return

    pending = st.session_state.get("order_edit_pending")

    if pending and pending.get("order_id") == order_id:
        st.warning("დარწმუნებული ხართ, რომ გსურთ ცვლილებების შენახვა?")
        st.caption(f"{pending['customer_name']} · {pending['phone']}")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button(
                "დიახ, შენახვა",
                type="primary",
                use_container_width=True,
                key=f"order_edit_yes_{order_id}",
            ):
                try:
                    db.update_order_customer_details(
                        order_id,
                        pending["customer_name"],
                        pending["phone"],
                        pending["address"],
                    )
                    _clear_order_action_state()
                    st.session_state.pop("order_edit_pending", None)
                    st.success("მომხმარებლის მონაცემები განახლდა!")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
        with col_no:
            if st.button("არა", use_container_width=True, key=f"order_edit_no_{order_id}"):
                st.session_state.pop("order_edit_pending", None)
                st.rerun()
        return

    with st.form(f"edit_order_customer_{order_id}"):
        edit_name = st.text_input("სახელი *", value=order["customer_name"])
        edit_phone = st.text_input("ტელეფონი *", value=order["phone"])
        edit_address = st.text_area("მისამართი *", value=order["address"])

        if st.form_submit_button("შენახვა", type="primary", use_container_width=True):
            if not edit_name.strip() or not edit_phone.strip() or not edit_address.strip():
                st.error("გთხოვთ, შეავსოთ ყველა სავალდებულო ველი.")
            else:
                st.session_state.order_edit_pending = {
                    "order_id": order_id,
                    "customer_name": edit_name.strip(),
                    "phone": edit_phone.strip(),
                    "address": edit_address.strip(),
                }
                st.rerun()


ACTIVE_ORDERS_TABLE_KEY = "active_orders_table"

COMPLETED_ORDER_STATUSES = ("მიწოდებული", "ჩაბარდა")


def is_order_completed(order: dict) -> bool:
    return (
        order.get("is_deleted", 0) == 0
        and order["payment_status"] == "გადახდილი"
        and order["status"] in COMPLETED_ORDER_STATUSES
    )


def split_orders_by_category(orders: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    deleted = [o for o in orders if o.get("is_deleted", 0) == 1]
    active = [
        o
        for o in orders
        if o.get("is_deleted", 0) == 0 and not is_order_completed(o)
    ]
    completed = [o for o in orders if is_order_completed(o)]
    return active, completed, deleted


def build_active_orders_df(orders: list[dict]) -> pd.DataFrame:
    rows = []
    for o in orders:
        product_names = ", ".join(
            f"{i['product_name']} ×{i['quantity']}" for i in o["items"]
        )
        rows.append(
            {
                "№": format_order_id(o["id"]),
                "id": o["id"],
                "მომხმარებელი": o["customer_name"],
                "ტელეფონი": o["phone"],
                "პროდუქტები": product_names,
                "თანხა": format_currency(order_collected_amount(o)),
                "Net Revenue": format_currency(o.get("net_product_revenue") or 0),
                "სტატუსი": o["status"],
                "გადახდა": o["payment_status"],
                "თარიღი": o["created_at"][:10],
            }
        )
    return pd.DataFrame(rows)


def get_selected_order_id(orders: list[dict]) -> int | None:
    state = st.session_state.get(ACTIVE_ORDERS_TABLE_KEY)
    if state is None:
        return None

    selection = getattr(state, "selection", None)
    if selection is None:
        return None

    rows = getattr(selection, "rows", None)
    if not rows:
        return None

    row_idx = rows[0]
    if row_idx < 0 or row_idx >= len(orders):
        return None

    return int(orders[row_idx]["id"])


def build_deleted_archive_rows(orders: list[dict]) -> list[dict]:
    rows = []
    for o in orders:
        product_names = ", ".join(
            f"{i['product_name']} ×{i['quantity']}" for i in o["items"]
        )
        rows.append(
            {
                "№": format_order_id(o["id"]),
                "მომხმარებელი": o["customer_name"],
                "ტელეფონი": o["phone"],
                "მისამართი": o["address"],
                "პროდუქტები": product_names,
                "გადასახდელი": format_currency(order_collected_amount(o)),
                "Net Revenue": format_currency(o.get("net_product_revenue") or 0),
                "ფასდაკლება": format_currency(o.get("total_discount") or 0),
                "კურიერი": format_currency(o.get("actual_delivery_cost") or 0),
                "სტატუსი": o["status"],
                "გადახდა": o["payment_status"],
                "შეიქმნა": o["created_at"][:16],
                "წაიშალა": o["updated_at"][:16],
            }
        )
    return rows


def render_selected_order_details(order: dict):
    collected = order_collected_amount(order)
    net_revenue = order.get("net_product_revenue") or 0
    product_summary = ", ".join(
        f"{i['product_name']} ×{i['quantity']}" for i in order["items"]
    )

    render_order_card_header(order, collected)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.write("ტელეფონი", order["phone"])
        st.write("მისამართი", order["address"])
        st.metric("კლიენტის გადასახდელი", format_currency(collected))
        st.metric("Net Revenue", format_currency(net_revenue))
    with col_b:
        st.write("პროდუქტები", product_summary)
        st.write("თარიღი", order["created_at"][:16])
        discount = order.get("total_discount", 0) or 0
        courier_cost = order.get("actual_delivery_cost") or 0
        if discount > 0:
            st.write("ფასდაკლება", format_currency(discount))
        if courier_cost > 0:
            st.write("კურიერის ხარჯი", format_currency(courier_cost))
    with col_c:
        new_status = st.selectbox(
            "სტატუსის შეცვლა",
            db.ORDER_STATUSES,
            index=db.ORDER_STATUSES.index(order["status"]),
            key=f"status_{order['id']}",
        )
        new_payment = st.selectbox(
            "გადახდის სტატუსის შეცვლა",
            db.PAYMENT_STATUSES,
            index=db.PAYMENT_STATUSES.index(order["payment_status"]),
            key=f"payment_{order['id']}",
        )
        if st.button("სტატუსის განახლება", key=f"update_{order['id']}", type="primary"):
            try:
                if new_status != order["status"]:
                    db.update_order_status(order["id"], new_status)
                if new_payment != order["payment_status"]:
                    db.update_payment_status(order["id"], new_payment)
                st.success("შეკვეთის სტატუსი განახლდა!")
                st.rerun()
            except ValueError as e:
                st.error(str(e))


def _dismiss_new_order_dialog():
    st.session_state.show_new_order_dialog = False


@st.dialog("ახალი შეკვეთის გაფორმება", width="large", on_dismiss=_dismiss_new_order_dialog)
def create_new_order_dialog():
    products = db.get_all_products()
    in_stock = [p for p in products if p["stock"] > 0]

    if not in_stock:
        st.warning("მარაგში პროდუქტები არ არის. ჯერ დაამატეთ პროდუქტები.")
        if st.button("დახურვა", use_container_width=True, key="new_order_dialog_close_empty"):
            _dismiss_new_order_dialog()
            st.rerun()
        return

    if "cart_items" not in st.session_state:
        st.session_state.cart_items = []

    col_info, col_cart = st.columns([1, 1])

    with col_info:
        st.markdown("**მომხმარებლის მონაცემები**")
        customer_name = st.text_input("სახელი *", key="cust_name", placeholder="გიორგი მ.")
        phone = st.text_input("ტელეფონი *", key="cust_phone", placeholder="5XX XX XX XX")
        address = st.text_area(
            "მისამართი *", key="cust_address", placeholder="ქალაქი, ქუჩა, სახლი..."
        )

        st.markdown("**ტრანსპორტირება**")
        actual_delivery_cost = st.number_input(
            "კურიერის რეალური ხარჯი (რა გადავუხადეთ კურიერს)",
            min_value=0.0,
            step=0.5,
            format="%.2f",
            value=0.0,
            key="actual_delivery_cost",
        )

    with col_cart:
        st.markdown("**პროდუქტების არჩევა**")
        product_options = {
            f"{p['name']} (მარაგი: {p['stock']}) — {format_currency(p['price'])}": p
            for p in in_stock
        }
        selected_label = st.selectbox("პროდუქტი", list(product_options.keys()))
        selected_product = product_options[selected_label]

        st.caption(f"ბაზის ფასი: {format_currency(selected_product['price'])}")
        final_unit_price = st.number_input(
            "პროდუქტის ფასი (ცალზე)",
            min_value=0.0,
            step=0.5,
            format="%.2f",
            value=float(selected_product["price"]),
            key=f"final_price_{selected_product['id']}",
        )
        quantity = st.number_input(
            "რაოდენობა",
            min_value=1,
            max_value=selected_product["stock"],
            step=1,
            key="order_qty",
        )

        if st.button("კალათაში დამატება", use_container_width=True):
            original_price = float(selected_product["price"])
            unit_price = float(final_unit_price)
            discount = max(0.0, original_price - unit_price)

            existing = next(
                (
                    i
                    for i in st.session_state.cart_items
                    if i["product_id"] == selected_product["id"]
                ),
                None,
            )
            if existing:
                new_qty = existing["quantity"] + quantity
                if new_qty > selected_product["stock"]:
                    st.error(
                        f"მარაგი არასაკმარისია (ხელმისაწვდომი: {selected_product['stock']})"
                    )
                else:
                    existing["quantity"] = new_qty
                    existing["original_price"] = original_price
                    existing["unit_price"] = unit_price
                    existing["discount"] = discount
                    st.rerun()
            else:
                st.session_state.cart_items.append(
                    {
                        "product_id": selected_product["id"],
                        "name": selected_product["name"],
                        "quantity": quantity,
                        "original_price": original_price,
                        "unit_price": unit_price,
                        "discount": discount,
                    }
                )
                st.rerun()

    if st.session_state.cart_items:
        st.markdown("**შეკვეთის შემადგენლობა**")
        cart_df = pd.DataFrame(
            [
                {
                    "პროდუქტი": item["name"],
                    "რაოდენობა": item["quantity"],
                    "საწყისი ფასი": format_currency(item["original_price"]),
                    "საბოლოო ფასი": format_currency(item["unit_price"]),
                    "ფასდაკლება": format_currency(item["discount"] * item["quantity"]),
                    "ჯამი": format_currency(item["unit_price"] * item["quantity"]),
                }
                for item in st.session_state.cart_items
            ]
        )
        st.dataframe(cart_df, use_container_width=True, hide_index=True)

        totals = calc_cart_totals(
            st.session_state.cart_items, float(actual_delivery_cost)
        )
        render_order_summary(totals)

        col_submit, col_clear = st.columns(2)
        with col_submit:
            if st.button("შეკვეთის გაფორმება", type="primary", use_container_width=True):
                if not customer_name.strip() or not phone.strip() or not address.strip():
                    st.error("გთხოვთ, შეავსოთ ყველა სავალდებულო ველი.")
                else:
                    try:
                        order_id = db.create_order(
                            customer_name.strip(),
                            phone.strip(),
                            address.strip(),
                            st.session_state.cart_items,
                            actual_delivery_cost=float(actual_delivery_cost),
                        )
                        st.session_state.cart_items = []
                        _dismiss_new_order_dialog()
                        st.success(f"შეკვეთა #{format_order_id(order_id)} წარმატებით შეიქმნა!")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
        with col_clear:
            if st.button("კალათის გასუფთავება", use_container_width=True):
                st.session_state.cart_items = []
                st.rerun()


def render_header():
    if LOGO_PATH.exists():
        logo_col, title_col = st.columns([1, 4], vertical_alignment="center")
        with logo_col:
            st.image(str(LOGO_PATH), width=200)
        with title_col:
            st.markdown('<p class="brand-title">Samarago</p>', unsafe_allow_html=True)
            st.markdown(
                '<p class="brand-subtitle">Facebook გაყიდვების მართვა</p>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<p class="brand-caption">პროდუქტები, შეკვეთები და სტატისტიკა ერთ ადგილას</p>',
                unsafe_allow_html=True,
            )
    else:
        st.title("Samarago — Facebook გაყიდვების მართვა")
        st.caption("პროდუქტები, შეკვეთები და სტატისტიკა ერთ ადგილას")

    st.divider()


def process_overdue_telegram_notifications():
    overdue_orders = db.get_overdue_unpaid_orders()
    for order in overdue_orders:
        order_id = int(order["id"])
        message = format_overdue_telegram_message(order)
        if send_telegram_message(message):
            db.update_order_telegram_sent(order_id)


def render_overdue_payment_alerts():
    overdue_orders = db.get_unacknowledged_payment_alerts()
    if not overdue_orders:
        return

    for order in overdue_orders:
        order_id = int(order["id"])
        alert_col, action_col = st.columns([5, 1])
        with alert_col:
            st.error(
                "⚠️ ყურადღება: "
                f"შეკვეთა #{format_order_id(order_id)}-ის "
                f"(კლიენტი: {order['customer_name']}) გადახდის 7-დღიანი ვადა ამოიწურა!"
            )
        with action_col:
            st.write("")
            if st.button(
                "გავეცანი",
                key=f"ack_payment_alert_{order_id}",
                use_container_width=True,
            ):
                try:
                    db.acknowledge_payment_alert(order_id)
                    st.rerun()
                except ValueError as e:
                    st.warning(str(e))


def tab_dashboard():
    metrics = db.get_dashboard_metrics()
    cols = st.columns(4)
    for col, (label, value) in zip(
        cols,
        [
            ("მთლიანი გაყიდვები", format_currency(metrics["total_sales"])),
            ("მთლიანი მოგება", format_currency(metrics["total_profit"])),
            ("მოლოდინში შეკვეთები", str(metrics["pending_orders"])),
            ("გადაუხდელი შეკვეთები", str(metrics["unpaid_orders"])),
        ],
    ):
        with col:
            st.metric(label, value)

    st.divider()
    st.subheader("📋 ბოლო შეკვეთები")

    orders = db.get_orders()[:10]
    if not orders:
        st.info("შეკვეთები ჯერ არ არის დამატებული.")
        return

    df = pd.DataFrame(build_orders_rows(orders))
    st.dataframe(style_orders_dataframe(df), width="stretch", hide_index=True)


def tab_products():
    if st.button("➕ ახალი პროდუქტის დამატება", type="primary"):
        st.session_state.show_new_product_dialog = True
        st.rerun()

    st.subheader("📦 პროდუქტების სია")

    products = db.get_all_products()
    if not products:
        st.info("პროდუქტები ჯერ არ არის დამატებული.")
    else:
        products_df = build_products_df(products)

        st.dataframe(
            style_products_dataframe(products_df),
            on_select="rerun",
            selection_mode="single-row",
            key=PRODUCTS_TABLE_KEY,
            use_container_width=True,
            hide_index=True,
        )

        selected_product_id = get_selected_product_id(products)
        if selected_product_id is not None:
            btn_edit, btn_delete = st.columns(2)
            with btn_edit:
                if st.button("📝 რედაქტირება", use_container_width=True, key="product_edit_btn"):
                    st.session_state.product_action = "edit"
                    st.session_state.product_action_id = selected_product_id
                    st.session_state.pop("product_edit_pending", None)
                    st.rerun()
            with btn_delete:
                if st.button("❌ წაშლა", use_container_width=True, key="product_delete_btn"):
                    st.session_state.product_action = "delete"
                    st.session_state.product_action_id = selected_product_id
                    st.rerun()

    if st.session_state.get("show_new_product_dialog"):
        add_new_product_dialog()

    if st.session_state.get("product_action") == "delete" and st.session_state.get("product_action_id"):
        confirm_delete_product_dialog(int(st.session_state.product_action_id))
    elif st.session_state.get("product_action") == "edit" and st.session_state.get("product_action_id"):
        edit_product_dialog(int(st.session_state.product_action_id))


def tab_orders():
    if st.button("➕ ახალი შეკვეთის გაფორმება", type="primary"):
        st.session_state.show_new_order_dialog = True
        st.rerun()

    all_orders = db.get_orders() + db.get_deleted_orders()
    active_orders, completed_orders, deleted_orders = split_orders_by_category(all_orders)

    tab_active, tab_completed, tab_deleted = st.tabs(
        ["🟢 აქტიური შეკვეთები", "✅ დასრულებული", "🗑️ წაშლილი"]
    )

    with tab_active:
        if not active_orders:
            st.info("აქტიური შეკვეთები ჯერ არ არის.")
        else:
            orders_df = build_active_orders_df(active_orders).drop(columns=["id"])

            st.dataframe(
                style_active_orders_dataframe(orders_df),
                on_select="rerun",
                selection_mode="single-row",
                key=ACTIVE_ORDERS_TABLE_KEY,
                use_container_width=True,
                hide_index=True,
            )

            selected_order_id = get_selected_order_id(active_orders)
            if selected_order_id is not None:
                btn_edit, btn_delete = st.columns(2)
                with btn_edit:
                    if st.button(
                        "📝 რედაქტირება",
                        use_container_width=True,
                        key="order_edit_btn",
                    ):
                        st.session_state.order_action = "edit"
                        st.session_state.order_action_id = selected_order_id
                        st.session_state.pop("order_edit_pending", None)
                        st.rerun()
                with btn_delete:
                    if st.button(
                        "❌ შეკვეთის წაშლა",
                        use_container_width=True,
                        key="order_delete_btn",
                    ):
                        st.session_state.order_action = "delete"
                        st.session_state.order_action_id = selected_order_id
                        st.rerun()

                selected_order = next(
                    o for o in active_orders if o["id"] == selected_order_id
                )
                with st.expander("არჩეული შეკვეთის დეტალები და სტატუსი", expanded=True):
                    render_selected_order_details(selected_order)

    with tab_completed:
        if not completed_orders:
            st.info("დასრულებული შეკვეთები ჯერ არ არის.")
        else:
            completed_df = build_active_orders_df(completed_orders).drop(columns=["id"])
            st.dataframe(
                style_orders_dataframe(completed_df),
                use_container_width=True,
                hide_index=True,
            )

    with tab_deleted:
        if not deleted_orders:
            st.info("წაშლილი შეკვეთები ჯერ არ არის.")
        else:
            archive_df = pd.DataFrame(build_deleted_archive_rows(deleted_orders))
            st.dataframe(
                style_orders_dataframe(archive_df),
                use_container_width=True,
                hide_index=True,
            )

    if st.session_state.get("show_new_order_dialog"):
        create_new_order_dialog()

    if st.session_state.get("order_action") == "delete" and st.session_state.get("order_action_id"):
        confirm_delete_order_dialog(int(st.session_state.order_action_id))
    elif st.session_state.get("order_action") == "edit" and st.session_state.get("order_action_id"):
        edit_order_customer_dialog(int(st.session_state.order_action_id))


def render_tab_navigation(current_tab: str) -> str:
    selected = st.radio(
        "ნავიგაცია",
        options=TAB_OPTIONS,
        index=TAB_OPTIONS.index(current_tab),
        format_func=lambda tab: TAB_LABELS[tab],
        horizontal=True,
        label_visibility="collapsed",
    )
    if selected != current_tab:
        st.query_params["tab"] = selected
        st.rerun()
    return selected


def main():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    render_header()
    process_overdue_telegram_notifications()
    render_overdue_payment_alerts()

    tab_param = st.query_params.get("tab", "დაფა")
    if isinstance(tab_param, list):
        tab_param = tab_param[0] if tab_param else "დაფა"
    current_tab = tab_param if tab_param in TAB_OPTIONS else "დაფა"
    if st.query_params.get("tab") != current_tab:
        st.query_params["tab"] = current_tab

    active_tab = render_tab_navigation(current_tab)

    if active_tab == "დაფა":
        tab_dashboard()
    elif active_tab == "პროდუქტები":
        tab_products()
    else:
        tab_orders()


if __name__ == "__main__":
    main()
