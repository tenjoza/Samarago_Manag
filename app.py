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
    page_title="Samarago",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+Georgian:wght@400;500;600;700&display=swap');

    :root {
        --samarago-orange: #FF8C00;
        --samarago-orange-dark: #E67E00;
        --samarago-orange-light: #FFF4E6;
        --text-primary: #0f172a;
        --text-secondary: #475569;
        --text-muted: #64748b;
        --glass-bg: rgba(255, 255, 255, 0.78);
        --glass-border: rgba(255, 255, 255, 0.65);
        --glass-radius: 15px;
        --glass-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    html, body, [class*="css"] {
        font-family: 'Inter', 'Noto Sans Georgian', sans-serif;
    }

    #MainMenu, footer, header[data-testid="stHeader"] {
        visibility: hidden;
    }

    .stApp {
        background: linear-gradient(145deg, #eef2f7 0%, #f8fafc 45%, #fff8ef 100%);
    }

    section[data-testid="stMain"] > div.block-container {
        background: transparent;
        box-shadow: none;
        border: none;
        padding: 0.5rem 1rem 1.25rem;
        max-width: 1200px;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--glass-bg);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border-radius: var(--glass-radius);
        box-shadow: var(--glass-shadow);
        border: 1px solid var(--glass-border);
        padding: 0.85rem 1rem 1rem;
        margin-bottom: 0.75rem;
        overflow: visible;
    }

    .section-card-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: var(--text-primary);
        margin: 0 0 0.65rem 0;
        padding-bottom: 0.45rem;
        border-bottom: 2px solid var(--samarago-orange-light);
    }

    h1, h2, h3 {
        color: var(--text-primary);
        letter-spacing: -0.01em;
    }

    h2, [data-testid="stMarkdownContainer"] h2 {
        font-size: 1.35rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.4rem !important;
    }

    hr {
        display: none;
    }

    div[data-testid="stTabs"] {
        background: var(--glass-bg);
        backdrop-filter: blur(12px);
        border-radius: var(--glass-radius);
        box-shadow: var(--glass-shadow);
        border: 1px solid var(--glass-border);
        padding: 0.35rem 0.5rem 0.75rem;
    }

    div[data-testid="stTabs"] [role="tablist"] {
        justify-content: center;
        gap: 0.35rem;
        flex-wrap: wrap;
    }

    div[data-testid="stTabs"] button {
        font-weight: 600;
        font-size: 0.92rem;
        min-height: 44px;
        padding: 0.5rem 0.75rem;
        border-radius: 10px;
    }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: var(--samarago-orange) !important;
        border-bottom-color: var(--samarago-orange) !important;
        background: var(--samarago-orange-light);
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stSegmentedControl"])
    [data-testid="stSegmentedControl"] {
        width: 100%;
        justify-content: center;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stSegmentedControl"])
    [data-testid="stSegmentedControl"] button {
        font-weight: 600;
        font-size: 0.92rem;
        min-height: 44px;
        flex: 1;
    }

    .stButton > button {
        min-height: 44px;
        border-radius: 12px;
        font-size: 1rem;
        font-weight: 600;
        padding: 0.55rem 1rem;
    }

    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {
        background-color: var(--samarago-orange) !important;
        border-color: var(--samarago-orange) !important;
        color: #ffffff !important;
        box-shadow: 0 4px 10px rgba(255, 140, 0, 0.28);
    }

    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover {
        background-color: var(--samarago-orange-dark) !important;
        border-color: var(--samarago-orange-dark) !important;
    }

    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea,
    div[data-baseweb="select"] > div {
        min-height: 44px;
        font-size: 1rem;
        border-radius: 12px !important;
        background: #ffffff !important;
    }

    .stTextArea textarea {
        min-height: 96px;
        padding: 0.7rem 0.8rem;
    }

    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid #e8edf3;
        border-radius: var(--glass-radius);
        padding: 0.7rem 0.9rem;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
    }

    /* Table chrome only — height is set per widget via the dynamic height helper */
    [data-testid="stDataFrame"],
    [data-testid="stDataFrameResizable"],
    div[data-testid="stDataEditor"],
    div[data-testid="stTable"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: var(--glass-radius);
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
    }

    .table-page-label {
        text-align: center;
        margin: 0.45rem 0 0;
        font-weight: 600;
        color: var(--text-secondary);
        font-size: 0.92rem;
    }

    div[data-testid="stAlert"] {
        border-radius: var(--glass-radius);
        margin-bottom: 0.45rem;
    }

    div[data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.9);
        border-radius: var(--glass-radius);
        border: 1px solid #e2e8f0;
        box-shadow: var(--glass-shadow);
    }

    /* Colored order-status pills inside order details */
    div[data-testid="stExpanderDetails"] [data-testid="stPills"] button {
        border-radius: 999px !important;
        font-weight: 600 !important;
        min-height: 40px !important;
        border: 2px solid transparent !important;
    }

    div[data-testid="stExpanderDetails"] [data-testid="stPills"] button[aria-pressed="true"] {
        border-color: var(--samarago-orange) !important;
        box-shadow: 0 2px 8px rgba(255, 140, 0, 0.28) !important;
    }

    div[data-testid="stExpanderDetails"] div[data-testid="stHorizontalBlock"]:last-of-type > div[data-testid="column"]:nth-child(1) [data-testid="stPills"] button:nth-child(1) {
        background-color: #fef08a !important;
        color: #854d0e !important;
    }

    div[data-testid="stExpanderDetails"] div[data-testid="stHorizontalBlock"]:last-of-type > div[data-testid="column"]:nth-child(1) [data-testid="stPills"] button:nth-child(2) {
        background-color: #bfdbfe !important;
        color: #1e40af !important;
    }

    div[data-testid="stExpanderDetails"] div[data-testid="stHorizontalBlock"]:last-of-type > div[data-testid="column"]:nth-child(1) [data-testid="stPills"] button:nth-child(3) {
        background-color: #bbf7d0 !important;
        color: #166534 !important;
    }

    div[data-testid="stExpanderDetails"] div[data-testid="stHorizontalBlock"]:last-of-type > div[data-testid="column"]:nth-child(1) [data-testid="stPills"] button:nth-child(4) {
        background-color: #fecaca !important;
        color: #b91c1c !important;
    }

    div[data-testid="stExpanderDetails"] div[data-testid="stHorizontalBlock"]:last-of-type > div[data-testid="column"]:nth-child(2) [data-testid="stPills"] button:nth-child(1) {
        background-color: #fecaca !important;
        color: #b91c1c !important;
    }

    div[data-testid="stExpanderDetails"] div[data-testid="stHorizontalBlock"]:last-of-type > div[data-testid="column"]:nth-child(2) [data-testid="stPills"] button:nth-child(2) {
        background-color: #bbf7d0 !important;
        color: #166534 !important;
    }

    .brand-title {
        font-size: 1.85rem;
        font-weight: 700;
        color: var(--samarago-orange);
        margin: 0;
        line-height: 1.2;
    }

    .brand-subtitle {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-secondary);
        margin: 0.15rem 0 0.2rem 0;
    }

    .brand-caption {
        font-size: 0.9rem;
        color: var(--text-muted);
        margin: 0;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:has(.brand-title) [data-testid="stImage"] img {
        border-radius: 12px;
    }

    @media (max-width: 768px) {
        section[data-testid="stSidebar"] {
            display: none !important;
        }

        section[data-testid="stMain"] > div.block-container {
            padding: 0.35rem 0.65rem 0.85rem;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(.brand-title) [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            align-items: center !important;
            text-align: center;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(.brand-title) [data-testid="stImage"] img {
            max-width: 168px;
            margin: 0 auto;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(.brand-title) .brand-title {
            font-size: 1.55rem;
        }

        .stButton > button {
            width: 100%;
        }

        div[data-testid="stTabs"] button {
            font-size: 0.8rem;
            padding: 0.4rem 0.45rem;
        }

        div[data-testid="column"] {
            min-width: 0;
        }
    }
</style>
"""

db.init_db()


def section_title(text: str):
    st.markdown(f'<p class="section-card-title">{text}</p>', unsafe_allow_html=True)

TAB_OPTIONS = ["დაფა", "პროდუქტები", "შეკვეთები"]
TAB_LABELS = {
    "დაფა": "📊 დაფა",
    "პროდუქტები": "📦 პროდუქტები",
    "შეკვეთები": "🛒 შეკვეთები",
}

DASHBOARD_PERIOD_OPTIONS = ("კვირა", "თვე", "წელი")
GEORGIAN_MONTHS = {
    1: "იანვარი",
    2: "თებერვალი",
    3: "მარტი",
    4: "აპრილი",
    5: "მაისი",
    6: "ივნისი",
    7: "ივლისი",
    8: "აგვისტო",
    9: "სექტემბერი",
    10: "ოქტომბერი",
    11: "ნოემბერი",
    12: "დეკემბერი",
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

ORDER_STATUS_PILL_LABELS = {
    "ახალი": "🟡 ახალი",
    "გაგზავნილი": "🔵 გაგზავნილი",
    "მიწოდებული": "🟢 მიწოდებული",
    "ჩაბარდა": "🟢 ჩაბარდა",
    "გაუქმებული": "🔴 გაუქმებული",
}

PAYMENT_STATUS_PILL_LABELS = {
    "გადაუხდელი": "🔴 გადაუხდელი",
    "გადახდილი": "🟢 გადახდილი",
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


def format_new_order_telegram_message(
    customer_name: str,
    phone: str,
    address: str,
    cart_items: list[dict],
    total_collected: float,
) -> str:
    if len(cart_items) == 1:
        product_name = cart_items[0]["name"]
        quantity = cart_items[0]["quantity"]
    else:
        product_name = ", ".join(
            f"{item['name']} ×{item['quantity']}" for item in cart_items
        )
        quantity = sum(item["quantity"] for item in cart_items)

    return (
        "🔔 <b>ახალი შეკვეთა გაფორმდა!</b>\n"
        f"👤 <b>კლიენტი:</b> {_display_field(customer_name)}\n"
        f"📞 <b>მობილური:</b> {_display_field(phone)}\n"
        f"🏠 <b>მისამართი:</b> {_display_field(address)}\n"
        f"📦 <b>პროდუქტი:</b> {_display_field(product_name)}\n"
        f"🔢 <b>რაოდენობა:</b> {quantity}\n"
        f"💰 <b>გადასახდელი თანხა:</b> {total_collected:,.2f} ₾"
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


def orders_table_column_config() -> dict:
    """Width hints only — conditional cell colors come from pandas Styler."""
    return {
        "სტატუსი": st.column_config.Column("სტატუსი", width="small"),
        "გადახდა": st.column_config.Column("გადახდა", width="small"),
    }


def products_table_column_config() -> dict:
    return {
        "ფასი (₾)": st.column_config.NumberColumn("ფასი (₾)", format="%.2f"),
        "თვითღირებულება (₾)": st.column_config.NumberColumn(
            "თვითღირებულება (₾)", format="%.2f"
        ),
        "ნაშთი": st.column_config.NumberColumn("ნაშთი", format="%d"),
    }


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
                "მოგება": format_currency(o.get("net_product_revenue") or 0),
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
    with st.container(border=True):
        section_title("შეკვეთის შეჯამება")
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
            label="პროდუქტის რეალური გასაყიდი ფასი (მოგება)",
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


def _on_order_status_pill_change(order_id: int):
    key = f"order_status_pills_{order_id}"
    new_status = st.session_state.get(key)
    if not new_status:
        return

    order = db.get_order_by_id(order_id)
    if not order or new_status == order["status"]:
        return

    try:
        db.update_order_status(order_id, new_status)
        st.toast("სტატუსი განახლდა", icon="✅")
        st.rerun()
    except ValueError as e:
        st.error(str(e))


def _on_payment_status_pill_change(order_id: int):
    key = f"order_payment_pills_{order_id}"
    new_payment = st.session_state.get(key)
    if not new_payment:
        return

    order = db.get_order_by_id(order_id)
    if not order or new_payment == order["payment_status"]:
        return

    try:
        db.update_payment_status(order_id, new_payment)
        st.toast("გადახდის სტატუსი განახლდა", icon="✅")
        st.rerun()
    except ValueError as e:
        st.error(str(e))


def render_order_status_pills(order: dict):
    order_id = int(order["id"])
    status_key = f"order_status_pills_{order_id}"
    if status_key not in st.session_state:
        st.session_state[status_key] = order["status"]

    st.pills(
        "სტატუსი",
        options=db.ORDER_STATUSES,
        default=order["status"],
        format_func=lambda status: ORDER_STATUS_PILL_LABELS.get(status, status),
        label_visibility="visible",
        width="stretch",
        key=status_key,
        on_change=_on_order_status_pill_change,
        kwargs={"order_id": order_id},
    )


def render_payment_status_pills(order: dict):
    order_id = int(order["id"])
    payment_key = f"order_payment_pills_{order_id}"
    if payment_key not in st.session_state:
        st.session_state[payment_key] = order["payment_status"]

    st.pills(
        "გადახდა",
        options=db.PAYMENT_STATUSES,
        default=order["payment_status"],
        format_func=lambda status: PAYMENT_STATUS_PILL_LABELS.get(status, status),
        label_visibility="visible",
        width="stretch",
        key=payment_key,
        on_change=_on_payment_status_pill_change,
        kwargs={"order_id": order_id},
    )


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
TABLE_PAGE_SIZE = 10
TABLE_ROW_HEIGHT_PX = 35
TABLE_MAX_HEIGHT_PX = 350


def table_height(df: pd.DataFrame) -> int:
    """Grow with row count up to 10 rows (350px), then cap."""
    return min((len(df) + 1) * TABLE_ROW_HEIGHT_PX, TABLE_MAX_HEIGHT_PX)


def paginate_df(df: pd.DataFrame, page_key: str) -> tuple[pd.DataFrame, int, int]:
    total_rows = len(df)
    total_pages = max(1, (total_rows + TABLE_PAGE_SIZE - 1) // TABLE_PAGE_SIZE)
    page = st.session_state.get(page_key, 0)
    page = max(0, min(int(page), total_pages - 1))
    st.session_state[page_key] = page
    start = page * TABLE_PAGE_SIZE
    end = start + TABLE_PAGE_SIZE
    return df.iloc[start:end].copy(), page, total_pages


def render_table_pagination(page_key: str, page: int, total_pages: int, total_rows: int):
    if total_rows <= TABLE_PAGE_SIZE:
        return

    _, center, _ = st.columns([1, 2, 1])
    with center:
        prev_col, label_col, next_col = st.columns([1, 1.2, 1])
        with prev_col:
            if st.button(
                "◀ წინა",
                key=f"{page_key}_prev",
                disabled=page == 0,
                use_container_width=True,
            ):
                st.session_state[page_key] = page - 1
                st.rerun()
        with label_col:
            st.markdown(
                f'<p class="table-page-label">{page + 1} / {total_pages}</p>',
                unsafe_allow_html=True,
            )
        with next_col:
            if st.button(
                "შემდეგი ▶",
                key=f"{page_key}_next",
                disabled=page >= total_pages - 1,
                use_container_width=True,
            ):
                st.session_state[page_key] = page + 1
                st.rerun()


def render_responsive_table(
    df: pd.DataFrame,
    style_func,
    page_key: str,
    *,
    table_key: str | None = None,
    on_select: str | None = None,
    selection_mode: str | None = None,
    column_config: dict | None = None,
) -> int:
    """Render up to 10 rows per page with adaptive height and styled cells."""
    page_df, page, total_pages = paginate_df(df, page_key)
    widget_kwargs: dict = {
        "use_container_width": True,
        "hide_index": True,
        "height": table_height(page_df),
    }
    if table_key:
        widget_kwargs["key"] = table_key
    if column_config:
        widget_kwargs["column_config"] = column_config
    if on_select:
        widget_kwargs["on_select"] = on_select
    if selection_mode:
        widget_kwargs["selection_mode"] = selection_mode

    st.dataframe(style_func(page_df), **widget_kwargs)
    render_table_pagination(page_key, page, total_pages, len(df))
    return page


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


def get_selected_product_id(products: list[dict], page: int = 0) -> int | None:
    state = st.session_state.get(PRODUCTS_TABLE_KEY)
    if state is None:
        return None

    selection = getattr(state, "selection", None)
    if selection is None:
        return None

    rows = getattr(selection, "rows", None)
    if not rows:
        return None

    row_idx = page * TABLE_PAGE_SIZE + rows[0]
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
                "მოგება": format_currency(o.get("net_product_revenue") or 0),
                "სტატუსი": o["status"],
                "გადახდა": o["payment_status"],
                "თარიღი": o["created_at"][:10],
            }
        )
    return pd.DataFrame(rows)


def get_selected_order_id(orders: list[dict], page: int = 0) -> int | None:
    state = st.session_state.get(ACTIVE_ORDERS_TABLE_KEY)
    if state is None:
        return None

    selection = getattr(state, "selection", None)
    if selection is None:
        return None

    rows = getattr(selection, "rows", None)
    if not rows:
        return None

    row_idx = page * TABLE_PAGE_SIZE + rows[0]
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
                "მოგება": format_currency(o.get("net_product_revenue") or 0),
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
    info_left, info_right = st.columns(2)
    with info_left:
        st.write("ტელეფონი", order["phone"])
        st.write("მისამართი", order["address"])
        st.metric("კლიენტის გადასახდელი", format_currency(collected))
        st.metric("მოგება", format_currency(net_revenue))
    with info_right:
        st.write("პროდუქტები", product_summary)
        st.write("თარიღი", order["created_at"][:16])
        discount = order.get("total_discount", 0) or 0
        courier_cost = order.get("actual_delivery_cost") or 0
        if discount > 0:
            st.write("ფასდაკლება", format_currency(discount))
        if courier_cost > 0:
            st.write("კურიერის ხარჯი", format_currency(courier_cost))

    st.divider()
    status_col, payment_col = st.columns(2)
    with status_col:
        render_order_status_pills(order)
    with payment_col:
        render_payment_status_pills(order)


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
        st.dataframe(
            cart_df,
            use_container_width=True,
            hide_index=True,
            height=table_height(cart_df),
        )

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
                        cart_snapshot = list(st.session_state.cart_items)
                        order_id = db.create_order(
                            customer_name.strip(),
                            phone.strip(),
                            address.strip(),
                            cart_snapshot,
                            actual_delivery_cost=float(actual_delivery_cost),
                        )
                        send_telegram_message(
                            format_new_order_telegram_message(
                                customer_name.strip(),
                                phone.strip(),
                                address.strip(),
                                cart_snapshot,
                                totals["total_collected"],
                            )
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
    with st.container(border=True):
        if LOGO_PATH.exists():
            logo_col, title_col = st.columns([1, 4], vertical_alignment="center")
            with logo_col:
                st.image(str(LOGO_PATH), width=180)
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
            st.markdown('<p class="brand-title">Samarago</p>', unsafe_allow_html=True)
            st.markdown(
                '<p class="brand-subtitle">Facebook გაყიდვების მართვა</p>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<p class="brand-caption">პროდუქტები, შეკვეთები და სტატისტიკა ერთ ადგილას</p>',
                unsafe_allow_html=True,
            )


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

    with st.container(border=True):
        section_title("გადახდის გაფრთხილებები")
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


def _dashboard_period_bounds() -> tuple[datetime, datetime]:
    period = st.session_state.get("dashboard_period", "კვირა")
    month = (
        st.session_state.get("dashboard_month", datetime.now().month)
        if period == "თვე"
        else None
    )
    return db.get_dashboard_period_bounds(period, month=month)


def render_dashboard_period_filters():
    with st.container(border=True):
        section_title("პერიოდი")
        filter_cols = st.columns([3, 2])
        with filter_cols[0]:
            st.radio(
                "პერიოდი",
                options=DASHBOARD_PERIOD_OPTIONS,
                horizontal=True,
                key="dashboard_period",
            )
        with filter_cols[1]:
            if st.session_state.get("dashboard_period") == "თვე":
                st.selectbox(
                    "თვე",
                    options=list(GEORGIAN_MONTHS.keys()),
                    format_func=lambda month: GEORGIAN_MONTHS[month],
                    index=datetime.now().month - 1,
                    key="dashboard_month",
                )


def tab_dashboard():
    render_dashboard_period_filters()
    period_start, period_end = _dashboard_period_bounds()
    metrics = db.get_dashboard_metrics(period_start, period_end)

    with st.container(border=True):
        section_title("საერთო სტატისტიკა")
        metric_cols = st.columns(5)
        for col, (label, value) in zip(
            metric_cols,
            [
                ("გადახდილი თანხა", format_currency(metrics["paid_revenue"])),
                ("მოლოდინში", format_currency(metrics["pending_revenue"])),
                ("მთლიანი მოგება", format_currency(metrics["total_profit"])),
                ("მოლოდინში შეკვეთები", str(metrics["pending_orders"])),
                ("გადაუხდელი შეკვეთები", str(metrics["unpaid_orders"])),
            ],
        ):
            with col:
                st.metric(label, value)

    with st.container(border=True):
        section_title("ბოლო შეკვეთები")
        orders = db.filter_orders_by_period(
            db.get_orders(),
            period_start,
            period_end,
        )
        if not orders:
            st.info("ამ პერიოდში შეკვეთები ჯერ არ არის.")
            return

        df = pd.DataFrame(build_orders_rows(orders))
        render_responsive_table(
            df,
            style_orders_dataframe,
            "dashboard_recent_orders_page",
            column_config=orders_table_column_config(),
        )


def tab_products():
    with st.container(border=True):
        if st.button("➕ ახალი პროდუქტის დამატება", type="primary", use_container_width=True):
            st.session_state.show_new_product_dialog = True
            st.rerun()

    with st.container(border=True):
        section_title("პროდუქტების სია")
        products = db.get_all_products()
        if not products:
            st.info("პროდუქტები ჯერ არ არის დამატებული.")
        else:
            products_df = build_products_df(products)
            products_page = render_responsive_table(
                products_df,
                style_products_dataframe,
                "products_page",
                table_key=PRODUCTS_TABLE_KEY,
                on_select="rerun",
                selection_mode="single-row",
                column_config=products_table_column_config(),
            )

            selected_product_id = get_selected_product_id(products, products_page)
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
    with st.container(border=True):
        if st.button("➕ ახალი შეკვეთის გაფორმება", type="primary", use_container_width=True):
            st.session_state.show_new_order_dialog = True
            st.rerun()

    all_orders = db.get_orders() + db.get_deleted_orders()
    active_orders, completed_orders, deleted_orders = split_orders_by_category(all_orders)

    with st.container(border=True):
        section_title("შეკვეთების მართვა")
        tab_active, tab_completed, tab_deleted = st.tabs(
            ["🟢 აქტიური შეკვეთები", "✅ დასრულებული", "🗑️ წაშლილი"]
        )

        with tab_active:
            if not active_orders:
                st.info("აქტიური შეკვეთები ჯერ არ არის.")
            else:
                orders_df = build_active_orders_df(active_orders).drop(columns=["id"])
                active_orders_page = render_responsive_table(
                    orders_df,
                    style_active_orders_dataframe,
                    "active_orders_page",
                    table_key=ACTIVE_ORDERS_TABLE_KEY,
                    on_select="rerun",
                    selection_mode="single-row",
                    column_config=orders_table_column_config(),
                )

                selected_order_id = get_selected_order_id(active_orders, active_orders_page)
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
                render_responsive_table(
                    completed_df,
                    style_orders_dataframe,
                    "completed_orders_page",
                    column_config=orders_table_column_config(),
                )

        with tab_deleted:
            if not deleted_orders:
                st.info("წაშლილი შეკვეთები ჯერ არ არის.")
            else:
                archive_df = pd.DataFrame(build_deleted_archive_rows(deleted_orders))
                render_responsive_table(
                    archive_df,
                    style_orders_dataframe,
                    "deleted_orders_page",
                    column_config=orders_table_column_config(),
                )

    if st.session_state.get("show_new_order_dialog"):
        create_new_order_dialog()

    if st.session_state.get("order_action") == "delete" and st.session_state.get("order_action_id"):
        confirm_delete_order_dialog(int(st.session_state.order_action_id))
    elif st.session_state.get("order_action") == "edit" and st.session_state.get("order_action_id"):
        edit_order_customer_dialog(int(st.session_state.order_action_id))


def render_main_navigation():
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "დაფა"

    with st.container(border=True):
        st.segmented_control(
            "ნავიგაცია",
            options=TAB_OPTIONS,
            format_func=lambda tab: TAB_LABELS[tab],
            label_visibility="collapsed",
            width="stretch",
            key="active_tab",
        )


def main():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    render_header()
    process_overdue_telegram_notifications()
    render_overdue_payment_alerts()

    render_main_navigation()

    if st.session_state.active_tab == "დაფა":
        tab_dashboard()
    elif st.session_state.active_tab == "პროდუქტები":
        tab_products()
    elif st.session_state.active_tab == "შეკვეთები":
        tab_orders()


if __name__ == "__main__":
    main()
