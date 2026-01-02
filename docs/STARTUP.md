# Startup & Setup Guide

Complete step-by-step instructions to set up and run the E-Commerce Backend on your local machine.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Dependency Installation](#dependency-installation)
4. [Environment Configuration](#environment-configuration)
5. [Database Initialization](#database-initialization)
6. [Starting the Server](#starting-the-server)
7. [Testing the API](#testing-the-api)
8. [Razorpay Test Mode](#razorpay-test-mode)
9. [Common Issues & Troubleshooting](#common-issues--troubleshooting)

---

## Prerequisites

Before starting, ensure you have the following installed:

### Required
- **Python 3.9+** ([download](https://www.python.org/downloads/))
- **pip** (comes with Python)
- **Git** ([download](https://git-scm.com/))
- **A text editor or IDE** (VSCode, PyCharm, etc.)

### Optional (Recommended)
- **Postman** or **Insomnia** (API testing tools)
- **Git GUI** (GitKraken, SourceTree)
- **Database viewer** (DB Browser for SQLite)

### Verify Installation
```bash
python --version        # Should be 3.9+
pip --version           # Should be 23+
git --version           # Should be 2.30+
```

---

## Environment Setup

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd "E_comm_BE"
```

### Step 2: Create Virtual Environment

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

After activation, you should see `(venv)` at the start of your terminal prompt.

### Step 3: Upgrade pip (Recommended)

```bash
pip install --upgrade pip setuptools wheel
```

---

## Dependency Installation

### Install Required Packages

```bash
pip install -r requirements.txt
```

This installs all dependencies including:
- fastapi, uvicorn (web framework)
- sqlalchemy, alembic (database)
- pydantic (validation)
- razorpay (payment gateway)
- python-jose (JWT)
- And 40+ others

### Verify Installation

```bash
pip list | grep -E "fastapi|sqlalchemy|uvicorn"
```

You should see something like:
```
fastapi          0.123.0
sqlalchemy       2.0.44
uvicorn          0.38.0
```

---

## Environment Configuration

### Step 1: Create `.env` File

Copy the example environment file:

```bash
cp .env.example .env
```

### Step 2: Configure Environment Variables

Edit the `.env` file with your values:

```bash
# Use your favorite editor:
nano .env           # Linux/macOS
code .env           # VSCode
```

### Example `.env` File

```env
# ============================================
# DATABASE
# ============================================
DATABASE_URL=sqlite:///./test.db

# ============================================
# JWT & SECURITY
# ============================================
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ============================================
# RAZORPAY (Test Mode)
# ============================================
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxx

# ============================================
# API
# ============================================
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=development

# ============================================
# LOGGING
# ============================================
LOG_LEVEL=INFO
```

### Where to Get Razorpay Test Keys

1. **Sign up** at [Razorpay Dashboard](https://dashboard.razorpay.com)
   - Use test mode (toggle available on dashboard)
   - **Never use production keys in development!**

2. **Copy test keys** from:
   - Dashboard → Settings → API Keys
   - Test mode toggle should be ON

3. **Paste into `.env`:**
   ```env
   RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx      # Copy from dashboard
   RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxx        # Copy from dashboard
   ```

### Generate JWT Secret

```bash
# Generate a secure random string:
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output into `.env`:
```env
JWT_SECRET_KEY=<paste-generated-token>
```

### ⚠️ Important Security Notes

- **Never commit `.env` to git** (it's in `.gitignore`)
- **Never share your secret keys**
- **Use environment-specific secrets** (dev/staging/prod)
- **Rotate secrets periodically** in production
- **Use a secrets manager** (AWS Secrets Manager, HashiCorp Vault) in production

---

## Database Initialization

### Step 1: Create Database Tables

Alembic migrations create the database schema:

```bash
alembic upgrade head
```

This command:
- Reads migration files from `alembic/versions/`
- Applies all pending migrations
- Creates tables: users, products, carts, orders, payments, inventory, etc.

**Expected output:**
```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl
INFO  [alembic.runtime.migration] Will assume non-transactional DDL
INFO  [alembic.migration] Running upgrade  -> xxxxx
...
```

### Step 2: Verify Database Creation

```bash
ls -la test.db    # Should show a new file
```

Or view with a database viewer (SQLite Browser):
```bash
sqlite3 test.db ".tables"
```

You should see tables like: `users`, `products`, `carts`, `orders`, `payments`, `inventory`, etc.

### Step 3: (Optional) Seed Test Data

Currently, there's no automatic seeding script. You can:

**Option A: Use API to create data**
- Create a user via `/users/register`
- Create a product via `/products` (admin only)
- Create inventory via `/inventory`

**Option B: Write a seed script**
Create `seed.py` in project root:
```python
from database import SessionLocal
from models.user_model import User
from models.product_model import Product

db = SessionLocal()
try:
    # Add test data here
    pass
finally:
    db.close()
```

Run: `python seed.py`

---

## Starting the Server

### Step 1: Activate Virtual Environment

If not already activated:

**macOS / Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```powershell
.\venv\Scripts\Activate.ps1
```

### Step 2: Start FastAPI Server

```bash
uvicorn main:app --reload
```

**Options:**
- `--reload` – Auto-restart on code changes (development only)
- `--host 0.0.0.0` – Listen on all network interfaces
- `--port 8000` – Use port 8000 (change if needed)

### Expected Output

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started server process [12345]
INFO:     Application startup complete
```

### Step 3: Verify Server is Running

Open in browser:
```
http://localhost:8000/docs
```

You should see the **Swagger UI** with all API endpoints listed.

---

## Testing the API

### Method 1: Using Swagger UI (Browser)

1. Open http://localhost:8000/docs
2. Click on an endpoint to expand it
3. Click "Try it out"
4. Enter values and click "Execute"

### Method 2: Using cURL (Terminal)

#### 1. Register a User
```bash
curl -X POST "http://localhost:8000/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Password123",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

**Expected response:**
```json
{
  "message": "User registered successfully",
  "status_code": 201,
  "data": {
    "id": 1,
    "email": "test@example.com",
    "first_name": "John"
  }
}
```

#### 2. Login
```bash
curl -X POST "http://localhost:8000/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Password123"
  }'
```

**Save the `access_token` from response** — you'll need it for other requests.

#### 3. Create a Product (Admin Only)

First, register an admin user or use the token from login.

```bash
curl -X POST "http://localhost:8000/products" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Laptop",
    "description": "High-performance laptop",
    "price": 999.99,
    "category": "Electronics",
    "sku": "LAP-001"
  }'
```

#### 4. Create Inventory for Product

```bash
curl -X POST "http://localhost:8000/inventory" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "stock": 100
  }'
```

#### 5. Add Product to Cart

```bash
curl -X POST "http://localhost:8000/cart/items" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "quantity": 2
  }'
```

#### 6. Create Order from Cart

```bash
curl -X POST "http://localhost:8000/orders" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "shipping_address": "123 Main St, City, Country",
    "payment_method": "CARD"
  }'
```

**Save the `order_id`** for payment testing.

#### 7. Create Payment Session

```bash
curl -X POST "http://localhost:8000/payments/create-session" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": 1
  }'
```

This returns:
```json
{
  "razorpay_order_id": "order_xxxxx",
  "amount": 199999,
  "currency": "INR",
  "key_id": "rzp_test_xxxxx",
  "order_id": 1
}
```

#### 8. Test Payment Verification

Use the test credentials below to simulate payment in Razorpay modal.

### Method 3: Using Postman

1. **Download Postman** from [postman.com](https://www.postman.com/downloads/)
2. **Create a new collection** named "E-Commerce API"
3. **Create requests** for each endpoint
4. **Set Authorization** to Bearer Token and use JWT tokens from login

**Sample Postman collection structure:**
```
E-Commerce API
├── Auth
│   ├── Register
│   ├── Login
│   └── Get Profile
├── Products
│   ├── List Products
│   ├── Create Product
│   └── Get Product
├── Cart
│   ├── Get Cart
│   ├── Add Item
│   └── Remove Item
├── Orders
│   ├── Create Order
│   ├── List Orders
│   └── Get Order
└── Payments
    ├── Create Session
    └── Verify Payment
```

---

## Razorpay Test Mode

### Test Cards

Use these cards in test mode (no real charges):

| Card Type | Card Number | Expiry | CVV |
|-----------|------------|--------|-----|
| **Visa** | 4111 1111 1111 1111 | Any future date | Any 3 digits |
| **Mastercard** | 5555 5555 5555 4444 | Any future date | Any 3 digits |
| **Test Fail** | 4000 0000 0000 0002 | Any future date | Any 3 digits |

### Simulating Payment in Razorpay Modal

When you open Razorpay checkout:

1. **Email:** Enter any email
2. **Phone:** Enter any phone (10 digits, e.g., 9999999999)
3. **Card Number:** Use test card above
4. **Expiry:** Use any future date (e.g., 12/25)
5. **CVV:** Use any 3 digits (e.g., 123)
6. **Name:** Enter any name
7. **Click Pay**

### Test Mode Features

- ✅ No real charges
- ✅ Instant settlement
- ✅ Full webhook support
- ✅ All card types available
- ✅ Error simulation available

### Switching Between Test & Live Mode

In [Razorpay Dashboard](https://dashboard.razorpay.com):
- Toggle button in top-right
- **Test Mode:** Shows "TEST MODE" banner
- **Live Mode:** Shows "LIVE MODE" (never use in development!)

---

## Common Issues & Troubleshooting

### Issue 1: "ModuleNotFoundError: No module named 'fastapi'"

**Cause:** Virtual environment not activated or dependencies not installed.

**Solution:**
```bash
# Activate virtual environment
source venv/bin/activate    # macOS/Linux
.\venv\Scripts\Activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

---

### Issue 2: "Address already in use" or "Port 8000 is already in use"

**Cause:** Another process is using port 8000.

**Solution:**
```bash
# Option A: Use a different port
uvicorn main:app --port 8001 --reload

# Option B: Kill the process using port 8000
lsof -ti:8000 | xargs kill -9      # macOS/Linux
netstat -ano | findstr :8000        # Windows (find PID then kill)
```

---

### Issue 3: "No such table: users" (Database error)

**Cause:** Migrations not applied.

**Solution:**
```bash
alembic upgrade head
```

---

### Issue 4: Razorpay API Errors ("Invalid API Key")

**Cause:** Incorrect keys in `.env`

**Solution:**
1. Check `.env` file has correct keys
2. Copy from [Razorpay Dashboard](https://dashboard.razorpay.com) again
3. Ensure **TEST MODE** is toggled ON
4. Restart server: `CTRL+C` then `uvicorn main:app --reload`

---

### Issue 5: "CORS error" or "Cross-Origin Request Blocked"

**Cause:** Frontend URL not in CORS allowed origins.

**Solution:**
In `main.py`, update CORS middleware:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # Your frontend URL
        "http://127.0.0.1:3000",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### Issue 6: "JWT token expired" or "Invalid token"

**Cause:** Token has expired or invalid format.

**Solution:**
```bash
# Login again to get a new token
curl -X POST "http://localhost:8000/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Password123"
  }'

# Use the new access_token in requests
```

---

### Issue 7: ".env file not found" or environment variables not loading

**Cause:** `.env` file not created or in wrong location.

**Solution:**
```bash
# Make sure you're in project root directory
pwd                             # Check current directory
ls -la .env                     # Check if .env exists

# If not, create it:
cp .env.example .env
nano .env                       # Edit with your values
```

---

### Issue 8: "Insufficient stock" error on order creation

**Cause:** No inventory created for product.

**Solution:**
```bash
# Create inventory first:
curl -X POST "http://localhost:8000/inventory" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "stock": 100
  }'
```

---

### Issue 9: Alembic migration errors

**Cause:** Database schema mismatch or migration issues.

**Solution:**
```bash
# Reset database (careful! deletes all data)
rm test.db
alembic downgrade base
alembic upgrade head

# Or view migration status:
alembic current
alembic heads
```

---

### Issue 10: "Permission denied" when running scripts

**Cause:** Script not executable on Linux/macOS.

**Solution:**
```bash
chmod +x venv/bin/activate
source venv/bin/activate
```

---

## Advanced Configuration

### Using PostgreSQL Instead of SQLite

For production-like testing:

1. **Install PostgreSQL** locally
2. **Update `.env`:**
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/ecommerce_db
   ```
3. **Install psycopg2:**
   ```bash
   pip install psycopg2-binary
   ```
4. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

---

### Enable Debug Logging

In `.env`:
```env
LOG_LEVEL=DEBUG
```

This shows more detailed logs including SQL queries.

---

### Hot Reload Development

Keep this running during development:
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Changes to Python files auto-reload automatically.

---

## Next Steps

1. ✅ Complete setup (database, `.env`, dependencies)
2. ✅ Start server (`uvicorn main:app --reload`)
3. ✅ Test API via Swagger UI or cURL
4. ✅ Create sample data (user, product, order)
5. ✅ Test payment flow with Razorpay test cards
6. 📖 Read [README.md](./README.md) for architecture details
7. 🔍 Explore source code to understand implementation
8. 💡 Modify code to experiment and learn

---

## Getting Help

- **API Documentation:** http://localhost:8000/docs
- **Code comments:** Check docstrings in services/
- **Logging:** Watch terminal output for detailed logs
- **Razorpay docs:** https://razorpay.com/docs/api/
- **FastAPI docs:** https://fastapi.tiangolo.com/
- **SQLAlchemy docs:** https://docs.sqlalchemy.org/

---

**Last Updated:** December 2025  
**Status:** Active Development
