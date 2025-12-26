# main.py

from fastapi import FastAPI
from database import Base, engine
from models.product_model import  Product, Category
from models.user_model import User  # just importing so tables are registered
from controllers.user_controller import router as user_router
from controllers.product_controller import router as product_router  # <-- new
from controllers.cart_controller import router as cart_router
from controllers.order_controller import router as order_router
from controllers.payment_controller import router as payment_router
from controllers.inventory_controller import router as inventory_router

from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from utils.exception_handler import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)

Base.metadata.create_all(bind=engine)

app = FastAPI()


app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],  # use explicit origin in production
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(user_router)
app.include_router(product_router)  
app.include_router(cart_router)
app.include_router(order_router)
app.include_router(payment_router)
app.include_router(inventory_router)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

