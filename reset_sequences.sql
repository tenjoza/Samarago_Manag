-- Run once after importing legacy data with fixed IDs.

SELECT setval(pg_get_serial_sequence('products', 'id'), COALESCE((SELECT MAX(id) FROM products), 1));
SELECT setval(pg_get_serial_sequence('orders', 'id'), COALESCE((SELECT MAX(id) FROM orders), 1));
SELECT setval(pg_get_serial_sequence('order_items', 'id'), COALESCE((SELECT MAX(id) FROM order_items), 1));
SELECT setval(pg_get_serial_sequence('delivery_rates', 'id'), COALESCE((SELECT MAX(id) FROM delivery_rates), 1));
