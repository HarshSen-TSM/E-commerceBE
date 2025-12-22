# main.py

from fastapi import FastAPI
from database import Base, engine
from models.product_model import  Product, Category
from models.user_model import User  # just importing so tables are registered
from Controllers.user_controller import router as user_router
from Controllers.product_controller import router as product_router  # <-- new
from Controllers.cart_controller import router as cart_router
from Controllers.order_controller import router as order_router
from Controllers.payment_controller import router as payment_router
from Controllers.inventory_controller import router as inventory_router

from fastapi.middleware.cors import CORSMiddleware


Base.metadata.create_all(bind=engine)

app = FastAPI()


app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],  # use explicit origin in production
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(user_router)
app.include_router(product_router)  # <-- new
app.include_router(cart_router)
app.include_router(order_router)
app.include_router(payment_router)
app.include_router(inventory_router)
