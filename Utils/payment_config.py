# Utils/payment_config.py
import os
from dotenv import load_dotenv

load_dotenv()  # if you're using a .env file

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_xxxxxxxxxxxx")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "xxxxxxxxxxxxxxxxxxxxxxx")

# Frontend will need KEY_ID to initialize Razorpay Checkout
