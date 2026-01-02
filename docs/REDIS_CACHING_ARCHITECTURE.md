# Redis Caching Architecture Report

**Generated:** December 30, 2025  
**Backend Type:** FastAPI E-commerce Backend  
**Current Database:** SQLite (test.db)  
**Redis Status:** ✅ Installed and ready

---

## 1. Project-Aware Overview

### Current Architecture
Your FastAPI backend follows a clean **3-layer architecture**:
- **Controllers** → API endpoints (routing only)
- **Services** → Business logic, orchestration, validation
- **Repositories** → Database access patterns

### Key Observations
1. **Read-Heavy Modules:**
   - Product listing with filters (search, category, price range)
   - User profile retrieval
   - Order history retrieval
   - Cart display

2. **Write-Heavy Modules:**
   - Order creation (complex multi-item transaction)
   - Payment verification (critical, no-cache operations)
   - Inventory management (stock mutation)
   - Cart mutations (add/remove items)

3. **Query Patterns Identified:**
   - `ProductService.list_products()` → Executes with 5+ filter combinations
   - `OrderService.list_user_orders()` → Uses `joinedload()` for eager loading (expensive)
   - `CartService.get_cart_for_user()` → Creates or retrieves, then builds response (aggregation)
   - Payment flows → **NO CACHING** (idempotency handled, critical operations)

4. **Expensive Operations:**
   - Product filtering with search + price range (ILIKE + numeric filters)
   - Order listing with joinedload(Order.items) (N+1 risk)
   - Cart calculation (subtotal, tax, discount, total)
   - Inventory stock checks (frequent reads, rare writes)

---

## 2. Redis Client Placement

### Where Redis Client Should Live
**File Path:** `utils/redis_client.py` (new file to create)

### Why a Centralized Client is Required
1. **Single Source of Truth:** All caching logic uses one Redis connection
2. **Connection Pooling:** Reuse connections across services (performance)
3. **Serialization Consistency:** JSON encoding/decoding in one place
4. **Centralized Configuration:** Host, port, DB number, TTL defaults managed together
5. **Dependency Injection Ready:** Services can import and use directly

### Redis Client Implementation
```python
# utils/redis_client.py
import redis
import json
from typing import Any, Optional
from utils.logger import logger

class RedisClient:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True
        )
        self._verify_connection()
    
    def _verify_connection(self):
        try:
            self.client.ping()
            logger.info("✅ Redis connection established")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache and deserialize"""
        try:
            value = self.client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.warning(f"Cache GET error | key={key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL"""
        try:
            self.client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.warning(f"Cache SET error | key={key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache DELETE error | key={key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache PATTERN DELETE error | pattern={pattern}: {e}")
            return 0

# Global instance
redis_client = RedisClient()
```

---

## 3. File-Level Caching Recommendations

### Product Module

#### ✅ Cache at Service Layer → `ProductService.list_products()`

**File:** [services/product_services.py](services/product_services.py)  
**Function:** `list_products()`

**What Data is Cached:**
- Product list with applied filters (search, category, price range)
- Includes full ProductRead serialization (id, name, description, price, status, image_url, stock)

**Cache Key Format:**
```
products:list:{skip}:{limit}:{search_hash}:{category_id}:{min_price}:{max_price}
```

**Suggested TTL:** 300 seconds (5 minutes)

**Why This Function is the Correct Caching Boundary:**
1. Service layer aggregates multiple filter conditions
2. Database query is expensive: `ILIKE` search + numeric comparisons
3. Read-only operation with **no side effects**
4. High cardinality (different filter combos), but most popular filters repeat
5. Cache invalidation is simple: only invalidate on product create/update/delete

**Why Caching Must NOT be Done Elsewhere:**
- ❌ **Controllers:** No business logic should touch controller layer; would leak concerns
- ❌ **Repositories:** Repository is data-access layer; caching at this level breaks abstraction
- ❌ **Models:** ORM models don't know about caching; creates tight coupling

**Implementation Pattern:**
```python
def list_products(
    self,
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> List[ProductRead]:
    # Build cache key
    search_hash = hashlib.md5((search or "").encode()).hexdigest()[:8]
    cache_key = f"products:list:{skip}:{limit}:{search_hash}:{category_id}:{min_price}:{max_price}"
    
    # Try cache
    cached = redis_client.get(cache_key)
    if cached:
        logger.info(f"Cache HIT: {cache_key}")
        return [ProductRead(**item) for item in cached]
    
    # Cache MISS: hit DB
    logger.info(f"Cache MISS: {cache_key}")
    products = product_repository.list_products(
        self.db,
        skip=skip,
        limit=limit,
        search=search,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
    )
    result = [ProductRead.model_validate(p) for p in products]
    
    # Store in cache (TTL: 5 min)
    redis_client.set(cache_key, [item.model_dump() for item in result], ttl=300)
    
    return result
```

**Cache Invalidation Strategy:**
- On `create_product()`: No invalidation needed (new products don't match existing filter queries)
- On `update_product()`: Invalidate `products:list:*` (use `delete_pattern()`)
- On `delete_product()`: Invalidate `products:list:*`

---

#### ✅ Cache at Service Layer → `ProductService.get_product()`

**File:** [services/product_services.py](services/product_services.py)  
**Function:** `get_product()`

**What Data is Cached:**
- Single product object (full detail: id, name, description, price, status, stock, category)

**Cache Key Format:**
```
product:{product_id}
```

**Suggested TTL:** 600 seconds (10 minutes)

**Why This Function is the Correct Caching Boundary:**
1. Frequently accessed: product detail pages, cart item validation, order creation lookup
2. Rarely changes: product details updated infrequently by admins
3. Service layer is business logic layer; perfect for performance optimization
4. Single lookup by ID; simplest caching pattern

**Why Caching Must NOT be Done Elsewhere:**
- ❌ **Repositories:** Would hide caching from service logic; service needs to control it
- ❌ **Models:** ORM models are anemic; don't belong in caching code
- ❌ **Controllers:** Controllers only route; never handle optimization

**Implementation Pattern:**
```python
def get_product(self, product_id: int) -> ProductRead:
    cache_key = f"product:{product_id}"
    
    # Try cache
    cached = redis_client.get(cache_key)
    if cached:
        logger.info(f"Cache HIT: {cache_key}")
        return ProductRead(**cached)
    
    # Cache MISS: hit DB
    logger.info(f"Cache MISS: {cache_key}")
    product = product_repository.get_product(self.db, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    result = ProductRead.model_validate(product)
    
    # Store in cache (TTL: 10 min)
    redis_client.set(cache_key, result.model_dump(), ttl=600)
    
    return result
```

**Cache Invalidation Strategy:**
- On `update_product(product_id)`: Invalidate `product:{product_id}`
- On `delete_product(product_id)`: Invalidate `product:{product_id}`

---

### User Module

#### ❌ DO NOT CACHE: `UserService.get_user()`

**File:** [services/user_services.py](services/user_services.py)  
**Function:** `get_user()`

**Why NO Caching:**
1. User data is **mutable:** email, password, address change frequently
2. Caching user objects creates **security risk:** stale auth context
3. **No performance bottleneck:** Simple primary-key lookup on small table
4. **Consistency critical:** Profile edits must be immediately visible
5. Admin roles could change: cached role would be stale

#### ❌ DO NOT CACHE: `UserService.list_users()`

**File:** [services/user_services.py](services/user_services.py)  
**Function:** `list_users()`

**Why NO Caching:**
1. Admin-only operation; rarely called (not a read-heavy endpoint)
2. User list changes frequently (new registrations)
3. Pagination makes cache key complex with minimal benefit
4. No performance issue: simple `SELECT * FROM users LIMIT X OFFSET Y`

#### ❌ DO NOT CACHE: `UserService.authenticate_user()` & `login()`

**File:** [services/user_services.py](services/user_services.py)  
**Functions:** `authenticate_user()`, `login()`

**Why NO Caching:**
1. **Security critical:** Never cache authentication results
2. **Password verification:** Must always hit database for security
3. **Rate limiting needed:** Cache would bypass rate-limit protection
4. **Token generation:** Must be fresh, not cached

---

### Cart Module

#### ⚠️ CONDITIONAL CACHE: `CartService.get_cart_for_user()`

**File:** [services/cart_services.py](services/cart_services.py)  
**Function:** `get_cart_for_user()`

**What Data is Cached:**
- Entire cart response: items array, subtotal, tax, discount, total

**Cache Key Format:**
```
cart:{user_id}
```

**Suggested TTL:** 60 seconds (1 minute) — VERY SHORT

**Why This Function is the Correct Caching Boundary:**
1. Cart aggregation is expensive: calculates subtotal, tax, discount, total
2. Cart is frequently read: displayed on page load, before checkout
3. **BUT:** Cart is mutable; cache must be SHORT-lived
4. Service layer handles aggregation logic

**Why Caching Must NOT be Done Elsewhere:**
- ❌ **Repositories:** Repository shouldn't know about cart summary calculations
- ❌ **Controllers:** Controllers only route requests
- ❌ **Models:** Models are passive data containers

**⚠️ CRITICAL CAVEAT:**
- Cache duration MUST be ≤60 seconds (1 minute)
- **Any cart mutation (add/remove/update) MUST immediately invalidate this cache**
- Without strict invalidation, users see stale cart totals

**Implementation Pattern:**
```python
def get_cart_for_user(self, user_id: int) -> CartRead:
    cache_key = f"cart:{user_id}"
    
    # Try cache (SHORT TTL for safety)
    cached = redis_client.get(cache_key)
    if cached:
        logger.info(f"Cache HIT: {cache_key}")
        return CartRead(**cached)
    
    # Cache MISS: hit DB
    cart = self._get_or_create_cart(user_id)
    result = self._build_cart_response(cart)
    
    # Store in cache (TTL: 60 sec only!)
    redis_client.set(cache_key, result.model_dump(), ttl=60)
    
    return result
```

**Cache Invalidation Strategy:**
- On `add_item()`: Immediately invalidate `cart:{user_id}`
- On `update_item_quantity()`: Immediately invalidate `cart:{user_id}`
- On `remove_item()`: Immediately invalidate `cart:{user_id}`
- On `clear_cart()`: Immediately invalidate `cart:{user_id}`

#### ❌ DO NOT CACHE: `CartService.add_item()`

**File:** [services/cart_services.py](services/cart_services.py)  
**Function:** `add_item()`

**Why NO Caching:**
1. **Mutation operation:** Cart state changes; caching doesn't apply
2. Must execute immediately (create/update logic)
3. Must invalidate cart summary cache after execution

---

### Order Module

#### ⚠️ SELECTIVE CACHE: `OrderService.list_user_orders()`

**File:** [services/order_services.py](services/order_services.py)  
**Function:** `list_user_orders()`

**What Data is Cached:**
- Full order list with items (eager-loaded via joinedload)

**Cache Key Format:**
```
user_orders:{user_id}
```

**Suggested TTL:** 180 seconds (3 minutes)

**Why This Function is the Correct Caching Boundary:**
1. Uses `joinedload(Order.items)` → expensive query (potential N+1 with serialization)
2. Read-only operation: users frequently check order history
3. **BUT:** Order status changes frequently (admin updates status)
4. Service layer orchestrates the complex query

**Why Caching Must NOT be Done Elsewhere:**
- ❌ **Repositories:** Repository shouldn't assume caching; violates single responsibility
- ❌ **Controllers:** Controllers only route

**⚠️ CRITICAL CAVEAT:**
- TTL is SHORT (3 minutes) because orders can be updated
- **Order status updates MUST invalidate this cache**
- Reason: User creates order → status is PENDING → user sees it in list → admin updates to SHIPPED → user refreshes and should see NEW status

**Implementation Pattern:**
```python
def list_user_orders(self, user_id: int) -> List[Order]:
    cache_key = f"user_orders:{user_id}"
    
    # Try cache
    cached = redis_client.get(cache_key)
    if cached:
        logger.info(f"Cache HIT: {cache_key}")
        # Reconstruct Order objects from cached dicts
        # Note: This is simplified; you may need more complex reconstruction
        return cached
    
    # Cache MISS: hit DB
    logger.info(f"Cache MISS: {cache_key}")
    orders = (
        self.db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .all()
    )
    
    # Serialize for cache
    result = [map_order_list(order) for order in orders]
    
    # Store in cache (TTL: 3 min)
    redis_client.set(cache_key, result, ttl=180)
    
    return orders
```

**Cache Invalidation Strategy:**
- On `create_order()`: Invalidate `user_orders:{user_id}` (new order added)
- On `update_status()`: Invalidate `user_orders:{*}` for all users (complex; consider pattern-based)
- On `get_order_for_user()`: **NO CACHING** (single-item lookups don't benefit; just cache full list)

#### ❌ DO NOT CACHE: `OrderService.create_order_from_cart()`

**File:** [services/order_services.py](services/order_services.py)  
**Function:** `create_order_from_cart()`

**Why NO Caching:**
1. **Critical mutation operation:** Creates order, reserves inventory, deletes cart items
2. **Race conditions possible:** Multiple concurrent requests could conflict
3. Idempotency is NOT achieved through caching (it's structural in payment flows)
4. Order creation is not read-heavy

#### ❌ DO NOT CACHE: `OrderService.get_order_for_user()`

**File:** [services/order_services.py](services/order_services.py)  
**Function:** `get_order_for_user()`

**Why NO Caching:**
1. Single-item lookup: cache miss is simple DB hit (not expensive)
2. Order details change (status updates); stale cache problematic
3. Low call frequency: Not a performance bottleneck
4. Use `list_user_orders()` cache instead (full order list is the expensive operation)

#### ❌ DO NOT CACHE: `OrderService.update_status()`

**File:** [services/order_services.py](services/order_services.py)  
**Function:** `update_status()`

**Why NO Caching:**
1. **Mutation operation:** Status changes; no caching applies
2. Must execute immediately
3. Must invalidate downstream caches (user's order list, single order cache)

---

### Payment Module

#### ❌❌❌ ABSOLUTELY DO NOT CACHE: Payment Operations

**File:** [services/payment_services.py](services/payment_services.py)  
**Functions:** `create_payment_session()`, `verify_and_capture_payment()`

**Why NO Caching (Strict Rule):**
1. **Financial transactions:** Caching payment state is dangerous
2. **Idempotency is built-in:** Uses `PENDING` status checks + unique constraints
3. **Race condition handling:** Uses DB-level mechanisms (IntegrityError catch)
4. **Razorpay integration:** Must hit Razorpay API; cannot cache external API calls
5. **Security:** Payment verification involves cryptographic signature checks (must be fresh)

---

### Inventory Module

#### ⚠️ SELECTIVE CACHE: Inventory Read-Only Queries

**File:** [repositories/inventory_repository.py](repositories/inventory_repository.py)  
**Function:** `get_by_product_id()` (called from service layer)

**What Data is Cached:**
- Inventory object: total_stock, available_stock, reserved_stock

**Cache Key Format:**
```
inventory:{product_id}
```

**Suggested TTL:** 120 seconds (2 minutes) — VERY SHORT

**Why Caching is Appropriate:**
1. Frequent lookups: checked during cart add, order creation, inventory display
2. Rarely changes: stock only changes on order events
3. **BUT:** Stock is CRITICAL; must invalidate immediately on mutations

**Why Caching Must NOT be Done Elsewhere:**
- ❌ **Repositories:** Inventory lookup must be in service that controls mutations
- Repository layer would cache but not know when to invalidate

**⚠️ CRITICAL CAVEAT:**
- TTL MUST be ≤120 seconds (2 minutes)
- **Every stock mutation MUST invalidate this cache immediately**
- Without strict invalidation, you get stale stock reads → overselling risk

**Implementation Pattern:**
Place caching in a service wrapper around inventory operations:

```python
# services/inventory_services.py (modified)
from utils.redis_client import redis_client

def get_inventory_cached(db: Session, product_id: int):
    cache_key = f"inventory:{product_id}"
    
    # Try cache
    cached = redis_client.get(cache_key)
    if cached:
        logger.info(f"Cache HIT: {cache_key}")
        # Reconstruct Inventory object
        return cached
    
    # Cache MISS
    inventory = get_by_product_id(db, product_id)
    if inventory:
        redis_client.set(cache_key, inventory.model_dump(), ttl=120)
    
    return inventory
```

**Cache Invalidation Strategy:**
- On `reserve_stock()`: Invalidate `inventory:{product_id}` (stock depleted)
- On `finalize_stock()`: Invalidate `inventory:{product_id}` (stock finalized)
- On `rollback_stock()`: Invalidate `inventory:{product_id}` (stock restored)

#### ❌ DO NOT CACHE: Stock Mutations

**File:** [services/inventory_services.py](services/inventory_services.py)  
**Functions:** `reserve_stock()`, `finalize_stock()`, `rollback_stock()`

**Why NO Caching:**
1. **Mutations:** Stock state changes; no caching applies
2. **Race condition sensitive:** Multiple concurrent orders can conflict
3. **Critical data:** Overselling is a business loss

---

## 4. Cache Key Naming Convention

### Standard Format
```
{module}:{operation}:{filter_criteria}
```

### Examples from Report
| Operation | Cache Key Pattern |
|-----------|------------------|
| Product list | `products:list:{skip}:{limit}:{search_hash}:{category_id}:{min_price}:{max_price}` |
| Product detail | `product:{product_id}` |
| User cart | `cart:{user_id}` |
| User orders | `user_orders:{user_id}` |
| Inventory | `inventory:{product_id}` |

### Rules
1. Use colons (`:`) as separators
2. Replace spaces/special chars in dynamic parts (e.g., search → hash)
3. Keep keys under 100 chars (Redis limit is 512MB, but human-readable wins)
4. Use lowercase for consistency

---

## 5. Cache Invalidation Strategies

### Pattern 1: Direct Key Invalidation (Single Item)
```python
# When single product is updated
redis_client.delete(f"product:{product_id}")
```

### Pattern 2: Pattern-Based Invalidation (Wildcard)
```python
# When ANY product is updated (invalidate all list caches)
redis_client.delete_pattern("products:list:*")
```

### Pattern 3: Immediate Invalidation After Write
```python
# After cart mutation, immediately clear cart cache
def add_item(self, user_id: int, data: CartItemCreate) -> CartRead:
    # ... add item logic ...
    redis_client.delete(f"cart:{user_id}")  # Invalidate IMMEDIATELY
    return self._build_cart_response(cart)  # Fresh read
```

### Pattern 4: TTL-Based Invalidation (Passive)
- No explicit deletion
- Cache expires after TTL seconds
- Useful for non-critical reads (product listings)
- Not safe for inventory/payments

---

## 6. Implementation Checklist

### Phase 1: Setup
- [ ] Create [utils/redis_client.py](utils/redis_client.py) with `RedisClient` class
- [ ] Add `redis>=4.5.0` to requirements.txt
- [ ] Test Redis connection on app startup
- [ ] Add logger statements in redis_client (connection, cache hits/misses)

### Phase 2: Product Module
- [ ] Add caching to `ProductService.list_products()`
- [ ] Add caching to `ProductService.get_product()`
- [ ] Add invalidation to `create_product()`, `update_product()`, `delete_product()`
- [ ] Test cache hits/misses with query logs

### Phase 3: Cart Module
- [ ] Add caching to `CartService.get_cart_for_user()` (TTL: 60 sec)
- [ ] Add invalidation to all cart mutations
- [ ] Test: Add item → cache invalidates → get_cart shows updated state

### Phase 4: Order Module
- [ ] Add caching to `OrderService.list_user_orders()` (TTL: 180 sec)
- [ ] Add invalidation to `create_order_from_cart()` and `update_status()`
- [ ] Test: Create order → cache invalidates → list shows new order

### Phase 5: Inventory Module
- [ ] Add inventory caching wrapper in service layer
- [ ] Invalidate on `reserve_stock()`, `finalize_stock()`, `rollback_stock()`
- [ ] Test: Reserve stock → cache invalidates → next read is fresh

### Phase 6: Monitoring
- [ ] Add cache hit/miss metrics to logger
- [ ] Monitor Redis memory usage
- [ ] Test TTL expiration scenarios
- [ ] Load test with concurrent requests

---

## 7. Performance Impact Summary

### Expected Improvements
| Operation | Bottleneck | Cache TTL | Expected Speedup |
|-----------|-----------|-----------|-----------------|
| Product listing | ILIKE search + filters | 300s | **3-5x** (complex query avoided) |
| Product detail | PK lookup | 600s | **1.5-2x** (less contention) |
| Cart display | Aggregation (subtotal/tax calc) | 60s | **2-3x** (calculation skipped) |
| Order listing | joinedload + N items | 180s | **2-4x** (expensive join avoided) |
| Inventory read | Simple lookup | 120s | **1.5-2x** (minimal latency) |

### Database Load Reduction
- Estimated **40-50% reduction** in read queries for high-traffic scenarios
- Write paths unaffected (intentionally)
- Payment paths unaffected (intentionally)

---

## 8. Risk Mitigation

### Risk 1: Stale Cart Data
**Scenario:** User adds item → sees stale total in cache → confusion  
**Mitigation:** TTL 60s (max 1 min stale), immediate invalidation on mutations

### Risk 2: Inventory Overselling
**Scenario:** Two concurrent orders see stale cache → both reserve same stock  
**Mitigation:** TTL 120s (very short), NO caching during stock mutations, DB constraints

### Risk 3: Payment Cache Corruption
**Scenario:** Payment state cached → user retries → sees stale status  
**Mitigation:** **ZERO caching** on payment operations (enforced)

### Risk 4: Redis Outage
**Scenario:** Redis down → entire system breaks  
**Mitigation:**
- All cache gets wrapped in try/except
- Cache misses gracefully degrade to DB hits
- No hard dependency on Redis

---

## 9. Monitoring & Debugging

### Metrics to Track
```python
# In redis_client.py, add:
self.cache_hits = 0
self.cache_misses = 0
self.cache_errors = 0

def get_stats(self):
    total = self.cache_hits + self.cache_misses
    hit_rate = (self.cache_hits / total * 100) if total > 0 else 0
    return {
        "hits": self.cache_hits,
        "misses": self.cache_misses,
        "errors": self.cache_errors,
        "hit_rate": f"{hit_rate:.1f}%"
    }
```

### Debug Endpoints (Optional)
```python
# In a debug router:
@router.get("/cache/stats")
def cache_stats():
    return redis_client.get_stats()

@router.post("/cache/clear")
def clear_all_cache():
    redis_client.delete_pattern("*")
    return {"status": "cleared"}
```

---

## 10. Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Controllers                   │
│  (product, cart, order, user, payment, inventory)        │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   Service Layer                          │
│  ┌─ ProductService       → list_products() [CACHE]      │
│  ├─ CartService         → get_cart() [CACHE-SHORT]      │
│  ├─ OrderService        → list_user_orders() [CACHE]    │
│  ├─ PaymentService      → [NO CACHE]                    │
│  ├─ InventoryService    → [CACHE WRAPPER ONLY]          │
│  └─ UserService         → [NO CACHE]                    │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼────────────┐       ┌────────▼────────────┐
│   Redis Cache      │       │   SQLite Database   │
│  (3-10 min TTL)    │       │   (Source of Truth) │
│                    │       │                     │
│ • Products         │       │ • All Tables        │
│ • Carts            │       │ • Transactions      │
│ • Orders           │       │ • Audit Logs        │
│ • Inventory        │       │                     │
└────────────────────┘       └─────────────────────┘
```

---

## 11. Conclusion

Your codebase is well-structured for caching integration:
- ✅ Service layer ready for cache logic
- ✅ Repositories don't leak queries up
- ✅ Clear separation of concerns
- ✅ Payment flows already idempotent (no cache interference)

**Recommended Implementation Order:**
1. Create Redis client utility (foundational)
2. Cache products (lowest risk, highest benefit)
3. Cache cart (medium complexity, quick wins)
4. Cache orders (complex invalidation, monitor carefully)
5. Monitor and optimize based on metrics

**Total Estimated Effort:** 3-4 hours for full implementation + testing

---

*Report generated by Harsh Sen*  
*Date: December 30, 2025*
