# Repositories/cart_repository.py

from typing import Optional, List
from sqlalchemy.orm import Session

from models.cart_model import Cart, CartItem
from models.product_model import Product


class CartRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- Cart ---
    def get_cart_by_user_id(self, user_id: int) -> Optional[Cart]:
        return (
            self.db.query(Cart)
            .filter(Cart.user_id == user_id, Cart.is_active == True)
            .first()
        )

    def create_cart_for_user(self, user_id: int) -> Cart:
        cart = Cart(user_id=user_id)
        self.db.add(cart)
        self.db.commit()
        self.db.refresh(cart)
        return cart

    # --- Cart items ---
    def get_item_by_id(self, item_id: int, cart_id: int) -> Optional[CartItem]:
        return (
            self.db.query(CartItem)
            .filter(CartItem.id == item_id, CartItem.cart_id == cart_id)
            .first()
        )

    def get_item_by_product(self, cart_id: int, product_id: int) -> Optional[CartItem]:
        return (
            self.db.query(CartItem)
            .filter(
                CartItem.cart_id == cart_id,
                CartItem.product_id == product_id,
            )
            .first()
        )

    def add_item(self, cart: Cart, product: Product, quantity: int) -> CartItem:
        item = self.get_item_by_product(cart.id, product.id)
        if item:
            item.quantity += quantity
        else:
            item = CartItem(
                cart_id=cart.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=product.price,
            )
            self.db.add(item)

        self.db.commit()
        self.db.refresh(item)
        self.db.refresh(cart)
        return item

    def update_item_quantity(self, item: CartItem, quantity: int) -> CartItem:
        item.quantity = quantity
        self.db.commit()
        self.db.refresh(item)
        return item

    def remove_item(self, item: CartItem) -> None:
        self.db.delete(item)
        self.db.commit()

    def clear_cart(self, cart: Cart) -> None:
        for item in list(cart.items):
            self.db.delete(item)
        self.db.commit()

    # --- Helper ---
    def get_product(self, product_id: int) -> Optional[Product]:
        return self.db.query(Product).filter(Product.id == product_id).first()
