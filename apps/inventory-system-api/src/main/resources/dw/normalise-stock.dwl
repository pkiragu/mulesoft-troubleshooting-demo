%dw 2.0
output application/json
---
{
    sku: payload.sku,
    storeId: payload.storeId,
    availableQuantity: payload.availableQuantity
}
