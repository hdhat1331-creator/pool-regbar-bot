import os

# --- اصلی ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "8958267630:AAGCqohmCZVWVtvbEh5GYpMjmXe1c1rmwgw")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8235703809"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://pool-regbar-bot.onrender.com")
PORT = int(os.getenv("PORT", "10000"))

# --- MongoDB ---
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://Amirkingef6677:Amirkingef6677@cluster0.bzg2v4m.mongodb.net/?appName=Cluster0"
)
DB_NAME = "pool_bot"

# --- تنظیمات ربات ---
INVITE_REWARD = 50000
SIGNUP_BONUS = 50000
REGULAR_MAX_MESSAGES = 50
REGULAR_MAX_LINES = 5
REGULAR_MAX_INVITES = 15
REGULAR_DELAY = 2.0
GOLD_MAX_MESSAGES = 3200
GOLD_DELAY = 0.05

GOLD_PLANS = {
    "gold_7": {"name": "۷ روزه", "days": 7, "price": 50000},
    "gold_14": {"name": "۱۴ روزه", "days": 14, "price": 100000},
    "gold_30": {"name": "یکماهه", "days": 30, "price": 120000},
}
