-- Run this in the Supabase SQL editor before using the app.

CREATE TABLE IF NOT EXISTS products (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    price DOUBLE PRECISION NOT NULL CHECK (price >= 0),
    cost DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (cost >= 0),
    weight DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (weight >= 0),
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    initial_stock INTEGER NOT NULL DEFAULT 0 CHECK (initial_stock >= 0),
    is_deleted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id BIGSERIAL PRIMARY KEY,
    customer_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ახალი',
    payment_status TEXT NOT NULL DEFAULT 'გადაუხდელი',
    total_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
    delivery_fee DOUBLE PRECISION NOT NULL DEFAULT 0,
    total_discount DOUBLE PRECISION NOT NULL DEFAULT 0,
    total_collected DOUBLE PRECISION NOT NULL DEFAULT 0,
    shipping_charged DOUBLE PRECISION NOT NULL DEFAULT 0,
    actual_delivery_cost DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (actual_delivery_cost >= 0),
    net_product_revenue DOUBLE PRECISION NOT NULL DEFAULT 0,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    payment_alert_sent INTEGER NOT NULL DEFAULT 0,
    telegram_alert_sent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price DOUBLE PRECISION NOT NULL,
    unit_cost DOUBLE PRECISION NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS delivery_rates (
    id BIGSERIAL PRIMARY KEY,
    city TEXT NOT NULL,
    weight_limit DOUBLE PRECISION NOT NULL CHECK (weight_limit > 0),
    price DOUBLE PRECISION NOT NULL CHECK (price >= 0),
    UNIQUE (city, weight_limit)
);
