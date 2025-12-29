# API Response Standardization

## Overview

This document outlines the standardized API response format for the E-commerce Backend application. Response standardization ensures consistent client-side handling, better error management, and improved API usability across all endpoints.

---

## Why Response Standardization?

### Problems Solved:
1. **Inconsistent Responses**: Different endpoints previously returned different formats (raw objects, raw lists, direct ORM models)
2. **Difficult Error Handling**: Clients couldn't reliably handle errors due to mixed response structures
3. **Poor Clarity**: No standard way to communicate success, failure, or metadata to clients
4. **Scalability Issues**: Adding new response features (pagination, timestamps) became complex
5. **Documentation Gaps**: API contract wasn't clear without examples

### Benefits:
- ✅ Predictable response structure for all endpoints
- ✅ Consistent error handling patterns
- ✅ Clear separation of concerns (HTTP status vs business status)
- ✅ Easy to version and evolve the API
- ✅ Better client-side code organization

---

## Standardized Response Format

### Success Response

**HTTP Status**: `200`, `201`, `204` (depending on operation)

```json
{
  "status_code": 200,
  "message": "Operation completed successfully",
  "data": {
    "id": 1,
    "name": "Product Name",
    "price": 99.99
  },
  "error": null
}
```

### Error Response

**HTTP Status**: `400`, `401`, `403`, `404`, `500`, etc.

```json
{
  "status_code": 400,
  "message": "Validation failed",
  "data": null,
  "error": "Email field is required"
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `status_code` | `int` | HTTP status code (mirrors HTTP response code) |
| `message` | `string` | Human-readable message describing the operation result |
| `data` | `object \| array \| null` | Response payload (null for errors or no-content responses) |
| `error` | `string \| null` | Error details if operation failed; null for successful operations |

---

## Response Examples by HTTP Method

### POST (Create)
```json
{
  "status_code": 201,
  "message": "Product created successfully",
  "data": {
    "id": 42,
    "name": "New Product",
    "category_id": 5
  },
  "error": null
}
```

### GET (Retrieve Single Resource)
```json
{
  "status_code": 200,
  "message": "Product retrieved successfully",
  "data": {
    "id": 42,
    "name": "Product Name",
    "price": 99.99
  },
  "error": null
}
```

### GET (Retrieve List)
```json
{
  "status_code": 200,
  "message": "Products retrieved successfully",
  "data": [
    {
      "id": 1,
      "name": "Product 1"
    },
    {
      "id": 2,
      "name": "Product 2"
    }
  ],
  "error": null
}
```

### PUT/PATCH (Update)
```json
{
  "status_code": 200,
  "message": "Product updated successfully",
  "data": {
    "id": 42,
    "name": "Updated Product Name"
  },
  "error": null
}
```

### DELETE (Remove)
```json
{
  "status_code": 200,
  "message": "Product deleted successfully",
  "data": {
    "id": 42,
    "name": "Deleted Product"
  },
  "error": null
}
```

### DELETE with No Content (204)
```json
{
  "status_code": 204,
  "message": "Cart cleared successfully",
  "data": null,
  "error": null
}
```

---

## HTTP Status Code Guidelines

| Code | Usage | Example |
|------|-------|---------|
| `200` | Successful GET, PUT, PATCH operations | Retrieve user profile |
| `201` | Successful POST (resource created) | Create new product |
| `204` | Successful DELETE (no content) | Clear cart |
| `400` | Bad request (validation error) | Missing required field |
| `401` | Unauthorized (invalid/missing token) | Expired token |
| `403` | Forbidden (no permission) | Non-admin trying to create product |
| `404` | Resource not found | Product ID doesn't exist |
| `500` | Server error | Unhandled exception |

---

## Helper Functions

### `success_response()`

Located in: `Utils/response_helper.py`

**Signature**:
```python
def success_response(
    message: str,
    data: Any = None,
    status_code: int = 200
) -> JSONResponse
```

**Parameters**:
- `message`: Human-readable success message
- `data`: Response payload (dict, list, Pydantic model, ORM model, or None)
- `status_code`: HTTP status code (200, 201, 204, etc.)

**Returns**: `JSONResponse` with standardized format

**Usage**:
```python
from Utils.response_helper import success_response

# Retrieve single resource
product = service.get_product(product_id)
return success_response(
    message="Product retrieved successfully",
    data=product
)

# Create resource
user = service.register_user(user_in)
return success_response(
    message="User registered successfully",
    data=user,
    status_code=201
)

# No content response
service.clear_cart(user_id)
return success_response(
    message="Cart cleared successfully",
    data=None,
    status_code=204
)
```

### `error_response()`

Located in: `Utils/response_helper.py`

**Signature**:
```python
def error_response(
    message: str,
    status_code: int = 400,
    error: str | None = None
) -> JSONResponse
```

**Parameters**:
- `message`: Human-readable error message
- `status_code`: HTTP status code (4xx or 5xx)
- `error`: Optional detailed error information

**Returns**: `JSONResponse` with standardized error format

**Note**: `error_response()` is currently not used in controllers (exception handling will be implemented later).

---

## Controller Implementation Guide

### Architecture Pattern: Controllers → Services → Repositories

```
┌──────────────────────────────────────────────────────────────┐
│ CONTROLLER (HTTP Layer)                                      │
│ - Receives HTTP request                                      │
│ - Calls service                                              │
│ - Wraps response with success_response()                    │
│ - Returns standardized JSON                                  │
└──────────────────────┬───────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│ SERVICE (Business Logic Layer)                               │
│ - Performs operations                                        │
│ - Returns raw data (no HTTP logic)                          │
│ - No knowledge of HTTP status codes                         │
└──────────────────────┬───────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│ REPOSITORY (Data Access Layer)                               │
│ - Queries database                                           │
│ - Returns ORM models or None                                │
│ - No business logic                                         │
└──────────────────────────────────────────────────────────────┘
```

### Key Rules

#### ✅ DO (Controller Responsibilities)

1. **Use `success_response()` for all success cases**
   ```python
   product = service.get_product(product_id)
   return success_response(
       message="Product retrieved successfully",
       data=product
   )
   ```

2. **Choose appropriate status codes**
   ```python
   # CREATE: 201
   user = service.register_user(user_in)
   return success_response(message="...", data=user, status_code=201)
   
   # READ: 200
   product = service.get_product(product_id)
   return success_response(message="...", data=product)
   
   # DELETE: 200 or 204
   service.delete_product(product_id)
   return success_response(message="...", data=None)
   ```

3. **Write clear, descriptive messages**
   ```python
   # ✅ Good
   "Product retrieved successfully"
   "User registered successfully"
   "Cart item updated successfully"
   
   # ❌ Poor
   "Success"
   "OK"
   "Done"
   ```

4. **Let services return raw data**
   ```python
   # Service returns raw dict or ORM model
   cart = service.get_cart_for_user(user_id)
   # Controller wraps it
   return success_response(message="Cart retrieved successfully", data=cart)
   ```

#### ❌ DON'T (Anti-patterns)

1. **Don't return raw dicts or models**
   ```python
   # ❌ WRONG
   return {"id": 1, "name": "Product"}
   
   # ❌ WRONG
   return product  # ORM model directly
   
   # ✅ CORRECT
   return success_response(message="...", data=product)
   ```

2. **Don't use `response_model` parameter**
   ```python
   # ❌ WRONG
   @router.get("/", response_model=List[ProductRead])
   
   # ✅ CORRECT
   @router.get("/")
   ```

3. **Don't return JSONResponse directly**
   ```python
   # ❌ WRONG
   return JSONResponse(content={...})
   
   # ✅ CORRECT
   return success_response(message="...", data=...)
   ```

4. **Don't add try/except in controllers**
   ```python
   # ❌ WRONG (for now)
   try:
       result = service.do_something()
       return success_response(message="...", data=result)
   except Exception as e:
       return error_response(message="...", error=str(e))
   
   # ✅ CORRECT (exception handling comes later)
   result = service.do_something()
   return success_response(message="...", data=result)
   ```

5. **Don't add business logic in controllers**
   ```python
   # ❌ WRONG
   @router.post("/products")
   def create_product(data: ProductCreate):
       if data.price < 0:  # Business logic in controller
           raise HTTPException(...)
       return success_response(...)
   
   # ✅ CORRECT
   @router.post("/products")
   def create_product(data: ProductCreate):
       product = service.create_product(data)  # Business logic in service
       return success_response(message="...", data=product)
   ```

---

## Before and After Examples

### Example 1: Get Product (GET)

#### BEFORE
```python
@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)):
    service = ProductService(db)
    return service.get_product(product_id)  # Returns raw ORM model
```

Response Body:
```json
{
  "id": 1,
  "name": "Product Name",
  "price": 99.99,
  "created_at": "2024-01-01T12:00:00"
}
```

#### AFTER
```python
@router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    service = ProductService(db)
    product = service.get_product(product_id)
    return success_response(
        message="Product retrieved successfully",
        data=product
    )
```

Response Body:
```json
{
  "status_code": 200,
  "message": "Product retrieved successfully",
  "data": {
    "id": 1,
    "name": "Product Name",
    "price": 99.99,
    "created_at": "2024-01-01T12:00:00"
  },
  "error": null
}
```

### Example 2: Create User (POST)

#### BEFORE
```python
@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, service: UserService = Depends(get_user_service)):
    return service.register_user(user_in)  # Returns raw user object
```

Response Body:
```json
{
  "id": 123,
  "email": "user@example.com",
  "name": "John Doe"
}
```

#### AFTER
```python
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, service: UserService = Depends(get_user_service)):
    user = service.register_user(user_in)
    return success_response(
        message="User registered successfully",
        data=user,
        status_code=201
    )
```

Response Body:
```json
{
  "status_code": 201,
  "message": "User registered successfully",
  "data": {
    "id": 123,
    "email": "user@example.com",
    "name": "John Doe"
  },
  "error": null
}
```

### Example 3: List Products (GET)

#### BEFORE
```python
@router.get("/", response_model=List[ProductRead])
def list_products(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    service = ProductService(db)
    return service.list_products(skip=skip, limit=limit)  # Returns raw list
```

Response Body:
```json
[
  {"id": 1, "name": "Product 1"},
  {"id": 2, "name": "Product 2"}
]
```

#### AFTER
```python
@router.get("/")
def list_products(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    service = ProductService(db)
    products = service.list_products(skip=skip, limit=limit)
    return success_response(
        message="Products retrieved successfully",
        data=products
    )
```

Response Body:
```json
{
  "status_code": 200,
  "message": "Products retrieved successfully",
  "data": [
    {"id": 1, "name": "Product 1"},
    {"id": 2, "name": "Product 2"}
  ],
  "error": null
}
```

### Example 4: Add to Cart (POST)

#### BEFORE
```python
@router.post("/items", response_model=CartRead)
def add_item_to_cart(item: CartItemCreate, db: Session = Depends(get_db), 
                     current_user: User = Depends(get_current_user)):
    service = CartService(db)
    return service.add_item(current_user.id, item)
```

Response Body (status: 200):
```json
{
  "id": 1,
  "user_id": 5,
  "items": [...]
}
```

#### AFTER
```python
@router.post("/items")
def add_item_to_cart(item: CartItemCreate, db: Session = Depends(get_db), 
                     current_user: User = Depends(get_current_user)):
    service = CartService(db)
    cart = service.add_item(current_user.id, item)
    return success_response(
        message="Item added to cart successfully",
        data=cart,
        status_code=201
    )
```

Response Body (status: 201):
```json
{
  "status_code": 201,
  "message": "Item added to cart successfully",
  "data": {
    "id": 1,
    "user_id": 5,
    "items": [...]
  },
  "error": null
}
```

---

## Service Layer Guidelines

Services **must NOT** be modified. They should:
- ✅ Accept business-level parameters
- ✅ Return raw data (dicts, ORM models, lists, primitives)
- ✅ Focus on business logic
- ✅ Have no knowledge of HTTP status codes or response formats
- ✅ Raise domain-specific exceptions for error handling

Example (unchanged):
```python
class ProductService:
    def get_product(self, product_id: int) -> Product:
        # Returns raw ORM model - NO HTTP LOGIC
        return self.repo.get_by_id(product_id)
    
    def create_product(self, data: ProductCreate) -> Product:
        # Returns raw ORM model - NO HTTP LOGIC
        return self.repo.create(data)
    
    def list_products(self, skip: int, limit: int) -> List[Product]:
        # Returns raw list - NO HTTP LOGIC
        return self.repo.list(skip=skip, limit=limit)
```

---

## Repository Layer Guidelines

Repositories **must NOT** be modified. They should:
- ✅ Query database and return ORM models
- ✅ Have no HTTP logic
- ✅ Have no business logic (beyond data access)
- ✅ Return None or raise exceptions for missing data

Example (unchanged):
```python
class ProductRepository:
    def get_by_id(self, product_id: int) -> Product | None:
        return self.db.query(Product).filter(...).first()
    
    def create(self, data: dict) -> Product:
        product = Product(**data)
        self.db.add(product)
        self.db.commit()
        return product
```

---

## Future Enhancements

The following enhancements are planned but **not** included in this update:

1. **Global Exception Handling**
   - Middleware to catch exceptions and convert to error_response format
   - Consistent error codes for different exception types

2. **Pagination Metadata**
   - Include `total`, `page`, `size` in response structure
   - Support cursor-based pagination

3. **Response Timestamps**
   - Add `timestamp` field to track when response was generated

4. **Request Tracing**
   - Include `request_id` in response for debugging

5. **Deprecation Warnings**
   - Add headers for deprecated endpoints

---

## Troubleshooting

### Issue: My response is double-wrapped

If you see a response like:
```json
{
  "status_code": 200,
  "message": "...",
  "data": {
    "status_code": 200,
    "message": "...",
    ...
  }
}
```

**Solution**: You're calling `success_response()` twice. The service already wrapped the response.

### Issue: Client receives 200 but data is null

If `data: null` when it shouldn't be:

1. Check if service is returning None
2. Verify you're capturing the service return value
3. Pass it to `success_response()`

```python
# ❌ WRONG
service.get_product(product_id)  # Result not captured
return success_response(message="...", data=None)  # data is None

# ✅ CORRECT
product = service.get_product(product_id)
return success_response(message="...", data=product)
```

### Issue: Status code doesn't match HTTP response

Ensure `status_code` in response matches the HTTP status:

```python
# ✅ CORRECT
return success_response(message="...", data=user, status_code=201)
# Returns HTTP 201 with status_code: 201 in body

# ❌ WRONG
return success_response(message="...", data=user, status_code=200)
# Returns HTTP 201 with status_code: 200 in body (mismatched)
```

---

## Quick Reference Checklist

When creating/updating a controller endpoint:

- [ ] Import `success_response` from `Utils.response_helper`
- [ ] Remove `response_model` from `@router.*` decorator
- [ ] Capture service return value in a variable
- [ ] Call `success_response(message="...", data=result)`
- [ ] Choose correct `status_code` (200, 201, 204)
- [ ] Write clear, descriptive message
- [ ] Do NOT add try/except (exception handling comes later)
- [ ] Do NOT add business logic (belongs in service)
- [ ] Do NOT return raw models or JSONResponse directly
- [ ] Test endpoint returns standardized format

---

## Additional Resources

- [FastAPI Response Documentation](https://fastapi.tiangolo.com/advanced/response-directly/)
- [HTTP Status Codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)
- [REST API Best Practices](https://restfulapi.net/http-status-codes/)
- [JSON API Standard](https://jsonapi.org/)

---

## Support

For questions or clarifications on response standardization:
1. Refer to examples in this document
2. Check modified controller files for reference implementations
3. Review `Utils/response_helper.py` for helper function source

