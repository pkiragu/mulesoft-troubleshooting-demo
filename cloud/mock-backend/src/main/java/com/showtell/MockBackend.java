package com.showtell;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

/** Single-replica, bounded, in-memory fictional warehouse. Restart resets all data. */
public final class MockBackend {
    private static final Map<String, Integer> stock = new HashMap<>();
    private static final Map<String, Map<String, Object>> reservations = new HashMap<>();
    private static final Map<String, Map<String, Object>> orders = new HashMap<>();
    private static final Map<String, String> orderByReservation = new HashMap<>();
    private static final int MAX_RESERVATIONS = 20000;
    static {
        for (String store : new String[]{"LONDON-01", "BRISTOL-02"}) {
            stock.put(store + "/LAPTOP-01", 100000);
            stock.put(store + "/HEADSET-02", 100000);
            stock.put(store + "/MONITOR-03", 0);
        }
    }
    private static Map<String, Object> response(int status, Object body) {
        return Map.of("status", status, "body", body);
    }
    private static Map<String, Object> error(int status, String code) {
        return response(status, Map.of("error", code));
    }
    private static int quantity(Object value) {
        if (!(value instanceof Number n) || n.doubleValue() <= 0 ||
                n.doubleValue() != Math.floor(n.doubleValue()) || n.doubleValue() > 100000) {
            throw new IllegalArgumentException("Invalid quantity");
        }
        return n.intValue();
    }
    public static synchronized Map<String, Object> dispatch(String method, String path,
            Map<String, Object> query, Map<String, Object> body) {
        try {
            if (method.equals("GET") && path.equals("/health"))
                return response(200, Map.of("status", "UP", "storage", "ephemeral", "synthetic", true));
            if (method.equals("GET") && path.equals("/stock")) {
                String store = String.valueOf(query.get("storeId"));
                String sku = String.valueOf(query.get("sku"));
                Integer qty = stock.get(store + "/" + sku);
                if (qty == null) return error(404, "STOCK_NOT_FOUND");
                Object wireQuantity = store.equals("BRISTOL-02") ? qty.toString() : qty;
                return response(200, Map.of("storeId", store, "sku", sku, "availableQuantity", wireQuantity));
            }
            if (method.equals("POST") && path.equals("/reservations")) {
                int qty = quantity(body.get("quantity"));
                String key = body.get("storeId") + "/" + body.get("sku");
                Integer available = stock.get(key);
                if (available == null || available < qty) return error(409, "OUT_OF_STOCK");
                if (reservations.size() >= MAX_RESERVATIONS) return error(503, "DEMO_CAPACITY_REACHED");
                String id = "res-" + UUID.randomUUID();
                reservations.put(id, Map.of("storeId", body.get("storeId"), "sku", body.get("sku"), "quantity", qty));
                stock.put(key, available - qty);
                return response(201, Map.of("reservationId", id));
            }
            if (method.equals("DELETE") && path.startsWith("/reservations/")) {
                String id = path.substring("/reservations/".length());
                if (orderByReservation.containsKey(id)) return error(409, "ORDER_ALREADY_CREATED");
                Map<String, Object> reservation = reservations.remove(id);
                if (reservation != null) {
                    String key = reservation.get("storeId") + "/" + reservation.get("sku");
                    stock.put(key, stock.get(key) + (Integer) reservation.get("quantity"));
                }
                return response(200, Map.of("released", true));
            }
            if (method.equals("POST") && path.equals("/orders")) {
                String rid = String.valueOf(body.get("reservationId"));
                if (orderByReservation.containsKey(rid)) return response(200, orders.get(orderByReservation.get(rid)));
                Map<String, Object> reservation = reservations.get(rid);
                if (reservation == null || !reservation.get("storeId").equals(body.get("storeId")) ||
                    !reservation.get("sku").equals(body.get("sku")) ||
                    (Integer) reservation.get("quantity") != quantity(body.get("quantity")))
                    return error(409, "INVALID_RESERVATION");
                String id = "ord-" + UUID.randomUUID();
                Map<String, Object> order = new LinkedHashMap<>(reservation);
                order.put("reservationId", rid);
                order.put("orderId", id);
                order.put("status", "READY_FOR_COLLECTION");
                orders.put(id, order);
                orderByReservation.put(rid, id);
                return response(201, order);
            }
            if (method.equals("GET") && path.startsWith("/orders/")) {
                Map<String, Object> order = orders.get(path.substring("/orders/".length()));
                return order == null ? error(404, "ORDER_NOT_FOUND") : response(200, order);
            }
            return error(404, "NOT_FOUND");
        } catch (IllegalArgumentException | NullPointerException ex) {
            return error(400, "BAD_REQUEST");
        }
    }
}
