# E-Commerce Backend API

A comprehensive **FastAPI + SQLAlchemy** e-commerce backend demonstrating professional backend architecture, payment integration, inventory management, and API design patterns.

> **Status:** Learning & Demo Project | **Database:** SQLite (dev) | **Payment:** Razorpay (test mode)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Key Features](#key-features)
4. [Tech Stack](#tech-stack)
5. [Folder Structure](#folder-structure)
6. [API Endpoints](#api-endpoints)
7. [Core Workflows](#core-workflows)
8. [Inventory Management](#inventory-management)
9. [Idempotency & Data Safety](#idempotency--data-safety)
10. [Project Status](#project-status)
11. [Disclaimer](#disclaimer)

---

## Overview

This e-commerce backend solves the core challenges of building a scalable online store:

- **User Management:** JWT authentication, profile management
- **Product Catalog:** Browse, filter, manage inventory
- **Shopping Cart:** Add, remove, update cart items
- **Order Processing:** Order creation, tracking, status management
- **Secure Payments:** Razorpay integration with signature verification
- **Inventory Control:** Real-time stock management with reservation and rollback logic
- **Data Integrity:** Saga pattern with compensating transactions (rollback on payment failure)

---

## Architecture

### 3-Tier Layered Architecture

```
┌─────────────────────────────────────────────────────┐
│              FastAPI Controllers                     │
│   (Routing, Request Validation, Response Mapping)    │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│            Service Layer                             │
│  (Business Logic, Transactions, Orchestration)       │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│          Repository Layer                            │
│   (Database Queries, ORM Abstraction)                │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│      SQLAlchemy ORM + SQLite Database                │
│    (Models, Tables, Constraints, Migrations)         │
└─────────────────────────────────────────────────────┘
```

### Design Patterns

- **3-Tier Layered Architecture:** Separation of concerns (routing → business logic → data access)
- **Repository Pattern:** Database queries abstracted into repositories
- **Service Layer:** Orchestration and business logic
- **Saga Pattern:** Compensating transactions for payment failure (inventory rollback)
- **Idempotency:** Payment verification is safe to retry

---

## Key Features

### 🔐 Authentication & Authorization
- JWT token-based authentication
- Role-based access control (user vs. admin)
- Password hashing with Argon2
- Secure token validation and refresh

### 📦 Product Management
- Create, read, update, delete products (admin only)
- Product categories and filtering
- Stock management integration
- Product pricing and discounts

### 🛒 Shopping Cart
- Add/remove items from cart
- Update quantities
- Calculate totals automatically
- Cart persistence per user

### 📋 Order Management
- Create orders from cart
- Real-time inventory reservation
- Order tracking and history
- Order status lifecycle (PENDING → PAID → SHIPPED → DELIVERED)
- Automatic cleanup of cart after order creation

### 💳 Payment Processing
- Razorpay integration (test mode)
- Payment session creation (idempotent)
- Cryptographic signature verification
- Payment status tracking (PENDING → SUCCESS → FAILED)
- Idempotent payment verification (safe to retry)

### 📊 Inventory Management
- Tri-state stock tracking:
  - **total_stock:** Physical inventory count
  - **available_stock:** Items ready to purchase
  - **reserved_stock:** Items reserved in pending orders
- Automatic stock reservation at order creation
- Rollback mechanism on payment failure
- Stock finalization on successful payment

### ⚡ Data Integrity & Safety
- ACID compliance via SQLAlchemy transactions
- Optimistic/pessimistic locking patterns
- Compensating transactions (Saga pattern)
- Unique constraints on critical records
- Comprehensive error handling and logging

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Framework** | FastAPI | 0.123+ |
| **ASGI Server** | Uvicorn | 0.38+ |
| **ORM** | SQLAlchemy | 2.0+ |
| **Migration Tool** | Alembic | 1.17+ |
| **Database** | SQLite (dev) | Built-in |
| **Authentication** | JWT + python-jose | 3.5+ |
| **Password Hashing** | Argon2 | 25.1+ |
| **Data Validation** | Pydantic | 2.12+ |
| **Payment Gateway** | Razorpay API | 2.0+ |
| **HTTP Client** | requests | 2.32+ |
| **Logging** | loguru | 0.7+ |
| **Environment** | python-dotenv | 1.2+ |

---

## Folder Structure

```
.
├── main.py                          # FastAPI app entry point
├── database.py                      # SQLAlchemy setup & session management
├── requirements.txt                 # Python dependencies
├── alembic.ini                      # Alembic configuration
│
├── alembic/
│   ├── env.py                       # Alembic environment config
│   ├── script.py.mako               # Alembic migration template
│   └── versions/                    # Database migration files
│       └── *.py                     # Migration scripts (applied via `alembic upgrade head`)
│
├── controllers/                     # API Route Handlers
│   ├── user_controller.py           # Auth, login, profile
│   ├── product_controller.py        # Product CRUD operations
│   ├── cart_controller.py           # Shopping cart operations
│   ├── order_controller.py          # Order creation & management
│   ├── payment_controller.py        # Payment session & verification
│   └── inventory_controller.py      # Inventory management (admin)
│
├── services/                        # Business Logic Layer
│   ├── user_services.py             # User registration, login, profile updates
│   ├── product_services.py          # Product operations
│   ├── cart_services.py             # Cart logic
│   ├── order_services.py            # Order creation & status updates
│   ├── payment_services.py          # Payment verification, signature checks
│   └── inventory_services.py        # Stock reservation, rollback, finalization
│
├── repositories/                    # Data Access Layer
│   ├── user_repository.py           # User DB queries
│   ├── product_repository.py        # Product DB queries
│   ├── cart_repository.py           # Cart DB queries
│   ├── order_repository.py          # Order DB queries
│   └── inventory_repository.py      # Inventory DB queries
│
├── models/                          # SQLAlchemy ORM Models
│   ├── user_model.py                # User table schema
│   ├── product_model.py             # Product & Category tables
│   ├── cart_model.py                # Cart & CartItem tables
│   ├── order_model.py               # Order & OrderItem tables
│   ├── payment_model.py             # Payment table
│   ├── inventory_model.py           # Inventory table
│   ├── address_model.py             # Address table
│   └── __init__.py
│
├── schemas/                         # Pydantic Request/Response Schemas
│   ├── user_schema.py               # User DTOs
│   ├── product_schema.py            # Product DTOs
│   ├── cart_schema.py               # Cart DTOs
│   ├── order_schema.py              # Order request/response schemas
│   ├── order_response.py            # Formatted order response
│   ├── payment_schema.py            # Payment DTOs
│   ├── inventory_schema.py          # Inventory DTOs
│   ├── response_schema.py           # Standardized API response wrapper
│   └── __init__.py
│
├── utils/                           # Helper Utilities
│   ├── jwt_utils.py                 # JWT token creation & validation
│   ├── logger.py                    # Centralized logging setup
│   ├── logging_filter.py            # Custom log filtering
│   ├── exception_handler.py         # Global exception handling
│   ├── response_helper.py           # Standardized response formatting
│   ├── request_context.py           # Request-scoped context
│   ├── payment_config.py            # Razorpay configuration
│   ├── razorpay_client.py           # Razorpay API client wrapper
│   └── mappers/
│       ├── order_mapper.py          # Order model to response schema mapping
│       └── __init__.py
│
├── frontend_test/                   # Frontend test HTML
│   └── index.html                   # Test UI for payment flow
│
├── .env.example                     # Environment variables template
├── README.md                        # This file
├── STARTUP.md                       # Setup and deployment guide
└── .gitignore                       # Excludes .env, *.db, __pycache__, etc.
```

---

## API Endpoints

### Authentication
```
POST   /users/register              Register new user
POST   /users/login                 Login & get JWT token
GET    /users/me                    Get current user profile
```

### Products
```
GET    /products                    List all products (paginated)
GET    /products/{product_id}       Get product details
POST   /products                    Create product (admin only)
PUT    /products/{product_id}       Update product (admin only)
DELETE /products/{product_id}       Delete product (admin only)
```

### Shopping Cart
```
GET    /cart                        Get current cart
POST   /cart/items                  Add item to cart
PUT    /cart/items/{item_id}        Update cart item quantity
DELETE /cart/items/{item_id}        Remove item from cart
DELETE /cart                        Clear entire cart
```

### Orders
```
POST   /orders                      Create order from cart
GET    /orders                      List user's orders
GET    /orders/{order_id}           Get order details
PATCH  /orders/{order_id}/status    Update order status (admin only)
```

### Payments
```
POST   /payments/create-session     Create Razorpay payment session
POST   /payments/verify             Verify payment signature & capture
```

### Inventory (Admin)
```
POST   /inventory                   Create inventory for product
GET    /inventory/{product_id}      Get inventory details
```

---

## Core Workflows

### 1. User Registration & Login
```
User inputs credentials
      ↓
Controller validates input
      ↓
Service hashes password with Argon2
      ↓
Service saves to database
      ↓
On login: Service verifies password & generates JWT
      ↓
Controller returns token to user
```

### 2. Shopping & Order Creation
```
User adds products to cart
      ↓
Cart service updates quantities
      ↓
User reviews cart → clicks "Checkout"
      ↓
OrderService.create_order_from_cart() executes:
   - Validates all items available
   - Locks inventory with with_for_update()
   - Reserves stock (available_stock ↓, reserved_stock ↑)
   - Creates OrderItem records
   - Calculates taxes & totals
   - Deletes cart items
   - Commits transaction
      ↓
Order created with status = PENDING
```

### 3. Payment Processing (Razorpay)
```
Frontend displays order summary
      ↓
Frontend calls /payments/create-session
      ↓
PaymentService creates Razorpay order (idempotent)
      ↓
Frontend opens Razorpay checkout modal
      ↓
Customer enters card details & submits
      ↓
Razorpay processes payment
      ↓
On success, Razorpay returns:
   - razorpay_order_id
   - razorpay_payment_id
   - razorpay_signature
      ↓
Frontend calls /payments/verify with signature
      ↓
PaymentService verifies signature using HMAC-SHA256
      ↓
If valid:
   - Payment.status = SUCCESS
   - Order.status = PAID
   - Stock finalized (reserved_stock → total_stock ↓)
   - Commit transaction
      ↓
If invalid:
   - Payment.status = FAILED
   - Inventory.reserved_stock → available_stock (rollback)
   - Order stays PENDING
   - Customer can retry payment
      ↓
Frontend shows result to customer
```

### 4. Inventory Lifecycle
```
Admin creates product with initial stock (total=100, available=100, reserved=0)

Order 1 created:
   Lock inventory
   Deduct from available → available=90, reserved=10
   Commit

Order 2 created concurrently:
   Wait for Order 1's lock
   Deduct from available → available=80, reserved=20
   Commit

Payment 1 succeeds:
   Finalize stock: reserved_stock → total_stock
   Result: total=90, available=90, reserved=20

Payment 2 fails:
   Rollback: reserved_stock → available_stock
   Result: total=90, available=100, reserved=0
   Order 2 becomes FAILED (can retry)
```

---

## Inventory Management

### Stock States

| State | Meaning | Example |
|-------|---------|---------|
| **total_stock** | Physical units owned | 100 units in warehouse |
| **available_stock** | Units ready to sell | 80 units (20 reserved) |
| **reserved_stock** | Units in pending orders | 20 units in checkout |

**Invariant:** `available_stock + reserved_stock ≤ total_stock`

### Reservation → Finalization → Rollback Flow

```
AVAILABLE STATE:
  available=100, reserved=0, total=100

ORDER CREATED (Stock Reserved):
  available=90, reserved=10, total=100
  ↓
  Customer proceeds to payment

PAYMENT SUCCESS (Stock Finalized):
  available=90, reserved=0, total=90
  ↓
  Order complete

PAYMENT FAILURE (Stock Rolled Back):
  available=100, reserved=0, total=100
  ↓
  Inventory restored for retry
```

### Key Functions

- **reserve_stock():** Decreases available, increases reserved (at order creation)
- **finalize_stock():** Decreases reserved & total (at payment success)
- **rollback_stock():** Increases available, decreases reserved (at payment failure)

---

## Idempotency & Data Safety

### Idempotent Payment Session Creation
- If customer refreshes the page during checkout, `/payments/create-session` reuses the existing PENDING payment
- No duplicate Razorpay orders are created
- Safe to call multiple times

### Idempotent Payment Verification
- If `/payments/verify` is called twice with same signature, returns same SUCCESS response
- Unique constraint on `(order_id, razorpay_payment_id)` prevents duplicate records
- Safe to retry if network fails

### Transaction Atomicity
- Order creation with stock reservation is a single atomic transaction
- If inventory lock fails, entire order creation rolls back
- Prevents partial orders with missing stock reservations

### Compensating Transactions (Saga Pattern)
- On payment failure, inventory is automatically rolled back
- Leaves system in consistent state
- Customer can create new order and retry payment

---

## Project Status

### ✅ Implemented
- User authentication (JWT)
- Product management
- Shopping cart
- Order creation with inventory reservation
- Payment session creation (idempotent)
- Payment verification with signature validation
- Inventory management (reserve, finalize, rollback)
- Logging and exception handling
- Database migrations (Alembic)
- API response standardization

### 🚧 In Development / Future
- Webhook handler for Razorpay events
- Order cancellation with full rollback
- Email notifications
- Admin dashboard
- Advanced inventory forecasting
- PostgreSQL for production
- Comprehensive test suite
- API documentation (Swagger/OpenAPI)
- Rate limiting
- Payment refunds & partial refunds

### ℹ️ Learning Focus
This project demonstrates:
- Professional backend architecture
- Payment gateway integration
- Transaction management
- Inventory control under concurrency
- ACID compliance
- Error handling & logging
- RESTful API design
- Database migrations

---

## Disclaimer

⚠️ **THIS IS A LEARNING & DEMO PROJECT** — Not intended for production use.

### Important Notes:

1. **Test Keys Only:** Uses Razorpay test mode credentials
   - Test card: `4111 1111 1111 1111` (any expiry, any CVV)
   - Real payments are NOT processed

2. **SQLite Database:** Development only
   - Not suitable for concurrent production workloads
   - Lacks true ACID compliance under high concurrency
   - Suggested migration: PostgreSQL for production

3. **Security Considerations:**
   - CORS is wide open (`allow_origins=["*"]`) — restrict in production
   - JWT secret is in `.env` — use secure key management
   - Password hashing is implemented correctly (Argon2)
   - API has no rate limiting — add in production

4. **No Webhook Handler:** 
   - Payment status relies on frontend callback
   - Production should implement Razorpay webhooks for reliability

5. **Intended Use:**
   - Learning platform design patterns
   - Interview review & discussion
   - Demonstration of backend skills
   - Educational reference

### For Production Deployment:
- Switch to PostgreSQL
- Implement Razorpay webhooks
- Restrict CORS origins
- Add comprehensive logging & monitoring
- Implement rate limiting & caching
- Add automated test suite
- Use environment-specific configuration
- Implement health checks & circuit breakers
- Add API versioning strategy

---

## Getting Started

For detailed setup instructions, see [STARTUP.md](./STARTUP.md).

Quick start:
```bash
# 1. Clone and setup environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Create .env file
cp .env.example .env
# Edit .env with your Razorpay test keys

# 3. Initialize database
alembic upgrade head

# 4. Start server
uvicorn main:app --reload

# 5. Open http://localhost:8000/docs for API documentation
```

---

## Contact & Questions

For questions about the architecture or design decisions, refer to the code comments and docstrings. Each major function includes intent and implementation notes.

---

**Last Updated:** December 2025  
**Author:** Harsh sen  
**License:** Educational Use Only
