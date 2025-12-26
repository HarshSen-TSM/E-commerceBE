# utils/mappers/order_mapper.py

def map_order_list(orders):
    return {
        "summary": {
            "total_orders": len(orders),
            "pending_orders": sum(1 for o in orders if o.status == "PENDING"),
            "total_amount": round(sum(o.grand_total for o in orders), 2),
        },
        "orders": [
            {
                "order_id": o.id,
                "items_count": o.total_items,
                "amount": float(o.grand_total),
                "status": o.status,
                "created_at": o.created_at.isoformat(timespec="seconds"),
                "payment_method": o.payment_method,
            }
            for o in orders
        ],
    }


def map_order_detail(order):
    return {
        "order": {
            "order_id": order.id,
            "status": order.status,
            "created_at": order.created_at.isoformat(timespec="seconds"),
            "shipping_address": order.shipping_address,
            "payment_method": order.payment_method,
        },
        "pricing": {
            "subtotal": float(order.subtotal),
            "tax": float(order.tax),
            "discount": float(order.discount),
            "grand_total": float(order.grand_total),
        },
        "items": [
            {
                "product_id": item.product_id,
                "product_name": item.product.name,
                "unit_price": float(item.unit_price),
                "quantity": item.quantity,
                "total_price": float(item.total_price),
            }
            for item in order.items
        ],
    }
