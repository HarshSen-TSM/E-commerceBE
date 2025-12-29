# Logger Usage Guide

Simple, development-focused logger for the E-commerce backend.

## How to Use

### 1. Import the logger
```python
from Utils.logger import logger
```

### 2. Log messages
```python
# Info level - for normal flow
logger.info("User login successful")
logger.info(f"Processing order {order_id}")

# Error level - for expected errors (validation, not found, etc.)
logger.error("Product not found")
logger.error(f"Order {order_id} validation failed: missing items")

# Exception level - for unexpected errors (catch Exception and log it)
try:
    payment = razorpay_client.order.create(...)
except Exception as e:
    logger.exception(f"Razorpay API failed: {str(e)}")
```

## Log Format

```
2025-12-11 14:30:45 | INFO     | ecommerce | User login successful
2025-12-11 14:30:46 | ERROR    | ecommerce | Product not found
2025-12-11 14:30:47 | ERROR    | ecommerce | Razorpay API failed: Connection timeout
```

Format breakdown:
- `timestamp` — When the log was written (YYYY-MM-DD HH:MM:SS)
- `level` — Log level (INFO, ERROR, EXCEPTION)
- `module` — Logger name (always "ecommerce")
- `message` — Your log message

## Example Usage in Services

### In `Services/payment_services.py`:
```python
from Utils.logger import logger

class PaymentService:
    def create_payment_session(self, user_id: int, data: PaymentSessionCreate):
        logger.info(f"Creating payment session for user {user_id}")
        
        try:
            order = db.query(Order).filter(...).first()
            if not order:
                logger.error(f"Order not found for user {user_id}")
                raise HTTPException(status_code=404, detail="Order not found")
            
            logger.info(f"Order total: ₹{order.grand_total}")
            
            razorpay_order = razorpay_client.order.create({...})
            logger.info(f"Razorpay order created: {razorpay_order['id']}")
            
            return response
        except Exception as e:
            logger.exception(f"Payment session creation failed: {str(e)}")
            raise
```

### In `Services/cart_services.py`:
```python
from Utils.logger import logger

class CartService:
    def add_item(self, user_id: int, data: CartItemCreate):
        logger.info(f"Adding product {data.product_id} to cart (user={user_id})")
        
        product = self.repo.get_product(data.product_id)
        if not product:
            logger.error(f"Product {data.product_id} not found")
            raise HTTPException(status_code=404, detail="Product not found")
        
        logger.info(f"Product added: {product.name} x {data.quantity}")
        return cart_response
```

## Key Points

✅ **Console only** — Logs go to stdout, perfect for development and Docker  
✅ **No duplicates** — Handler check prevents duplicate logs on uvicorn reload  
✅ **Thread-safe** — Works with FastAPI sync/async and threadpool functions  
✅ **Simple format** — Easy to read and grep for debugging  
✅ **3 log levels**:
  - `logger.info()` — Normal flow, tracking progress
  - `logger.error()` — Expected errors (validation, not found, permission denied)
  - `logger.exception()` — Unexpected errors (include traceback)

## Where to Add Logging

Good places to log:
- Entry point of a function (with key parameters)
- Before/after database operations
- Before/after API calls (Razorpay, external services)
- Validation failures
- Caught exceptions

Example:
```python
def process_order(order_id: int):
    logger.info(f"Processing order {order_id}")  # Entry
    
    order = db.query(Order).filter(...).first()
    if not order:
        logger.error(f"Order {order_id} not found")  # Validation
        raise HTTPException(...)
    
    logger.info(f"Order fetched: total={order.grand_total}")  # Progress
    
    try:
        payment = razorpay.create(...)
        logger.info(f"Payment initiated: {payment['id']}")  # Success
    except Exception as e:
        logger.exception(f"Payment failed: {str(e)}")  # Unexpected error
        raise
```

## Testing the Logger

Run this in your terminal to test:
```bash
cd /home/harsh/PHASE\ II/E-commerce/E_comm_BE
python -c "from Utils.logger import logger; logger.info('Test info'); logger.error('Test error')"
```

Expected output:
```
2025-12-11 14:30:45 | INFO     | ecommerce | Test info
2025-12-11 14:30:45 | ERROR    | ecommerce | Test error
```
