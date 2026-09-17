package com.showtell;
import java.util.Map;
public final class MockBackendCheck {
    private static Map<String,Object> body(Map<String,Object> response) {
        return (Map<String,Object>)response.get("body");
    }
    public static void main(String[] args) {
        Map<String,Object> london=Map.of("storeId","LONDON-01","sku","LAPTOP-01");
        Map<String,Object> bristol=Map.of("storeId","BRISTOL-02","sku","LAPTOP-01");
        assert body(MockBackend.dispatch("GET","/stock",london,Map.of())).get("availableQuantity") instanceof Integer;
        assert body(MockBackend.dispatch("GET","/stock",bristol,Map.of())).get("availableQuantity") instanceof String;
        Map<String,Object> reservation=body(MockBackend.dispatch("POST","/reservations",Map.of(),Map.of("storeId","LONDON-01","sku","LAPTOP-01","quantity",2)));
        String rid=(String)reservation.get("reservationId");
        Map<String,Object> input=Map.of("storeId","LONDON-01","sku","LAPTOP-01","quantity",2,"reservationId",rid);
        Map<String,Object> order=body(MockBackend.dispatch("POST","/orders",Map.of(),input));
        assert order.equals(body(MockBackend.dispatch("GET","/orders/"+order.get("orderId"),Map.of(),Map.of())));
        assert order.equals(body(MockBackend.dispatch("POST","/orders",Map.of(),input)));
        assert MockBackend.dispatch("DELETE","/reservations/"+rid,Map.of(),Map.of()).get("status").equals(409);
        assert MockBackend.dispatch("POST","/reservations",Map.of(),Map.of("storeId","LONDON-01","sku","MONITOR-03","quantity",1)).get("status").equals(409);
        assert MockBackend.dispatch("POST","/reservations",Map.of(),Map.of("storeId","LONDON-01","sku","LAPTOP-01","quantity",-1)).get("status").equals(400);
        System.out.println("Mock backend contract checks passed");
    }
}
