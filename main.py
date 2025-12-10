# main.py

from fastapi import FastAPI
from database import Base, engine
from models.product_model import  Product, Category
from models.user_model import User  # just importing so tables are registered
from Controllers.user_controller import router as user_router
from Controllers.product_controller import router as product_router  # <-- new
from Controllers.cart_controller import router as cart_router
from Controllers.order_controller import router as order_router


Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(user_router)
app.include_router(product_router)  # <-- new
app.include_router(cart_router)
app.include_router(order_router)
