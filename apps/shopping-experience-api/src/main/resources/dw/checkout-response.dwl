%dw 2.0
output application/json
---
{
    orderId: payload.orderId,
    status: payload.status,
    collection: {storeId: payload.storeId, message: "Your order is reserved for collection"},
    items: [{sku: payload.sku, quantity: payload.quantity}],
    correlationId: vars.traceId
}
