from flask import Flask, request, jsonify
import os
import json
import random
import string
import time
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = Flask(__name__)

TOKEN = "8958267630:AAGCqohmCZVWVtvbEh5GYpMjmXe1c1rmwgw"
BOT_USERNAME = os.getenv("BOT_USERNAME", "POOLREGBARR_BOT")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8235703809"))
SUPABASE_URL = "https://eqhhthempcgwlwrdxjfk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxaGh0aGVtcGNnd2x3cmR4amZrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc1NTc0MTcsImV4cCI6MjEwMzEzMzQxN30.XXdU59uidgB4Efb_nPXOWmG2fpLeWXfEgaE77M99E94"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

GOLD_PLANS = {
    "7": {"days": 7, "price": 50000, "name": "۷ روزه"},
    "14": {"days": 14, "price": 100000, "name": "۱۴ روزه"},
    "30": {"days": 30, "price": 120000, "name": "یکماهه"},
}

# ---------------- Database helpers ----------------

def load_db(table_name):
    try:
        result = supabase.table(table_name).select("*").execute()
        return {
            str(row["id"]): {k: v for k, v in row.items() if k != "id"}
            for row in (result.data or [])
            if "id" in row
        }
    except Exception as e:
        print(f"load_db({table_name}): {e}")
        return {}

def save_db(table_name, data):
    try:
        for key, value in data.items():
            row = dict(value)
            row["id"] = str(key)
            supabase.table(table_name).upsert(row).execute()
        return True
    except Exception as e:
        print(f"save_db({table_name}): {e}")
        return False

def load_users(): return load_db("users")
def save_users(x): return save_db("users", x)
def load_invites(): return load_db("invites")
def save_invites(x): return save_db("invites", x)
def load_messages(): return load_db("messages")
def save_messages(x): return save_db("messages", x)
def load_tickets(): return load_db("tickets")
def save_tickets(x): return save_db("tickets", x)
def load_gold_requests(): return load_db("gold_requests")
def save_gold_requests(x): return save_db("gold_requests", x)
def load_blocked(): return load_db("blocked")
def save_blocked(x): return save_db("blocked", x)
def load_banned(): return load_db("banned")
def save_banned(x): return save_db("banned", x)

# Settings are persisted in messages table under reserved IDs.
SETTINGS_PREFIX = "__settings__:"

def get_user_settings(user_id):
    messages = load_messages()
    value = messages.get(SETTINGS_PREFIX + str(user_id), {}).get("message")
    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}

def save_user_setting(user_id, key, value):
    settings = get_user_settings(user_id)
    settings[key] = value
    messages = load_messages()
    messages[SETTINGS_PREFIX + str(user_id)] = {"message": json.dumps(settings, ensure_ascii=False)}
    save_messages(messages)

def get_user_message(user_id):
    messages = load_messages()
    return messages.get(str(user_id), {}).get("message")

def save_user_message(user_id, message):
    messages = load_messages()
    messages[str(user_id)] = {"message": message}
    save_messages(messages)

# ---------------- Utility ----------------

def generate_ref_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def get_user(user_id):
    return load_users().get(str(user_id))

def is_admin(user_id):
    return int(user_id) == ADMIN_ID

def is_blocked(user_id):
    return str(user_id) in load_blocked()

def is_banned(user_id):
    banned = load_banned()
    item = banned.get(str(user_id))
    if not item:
        return False
    if item.get("type") == "permanent":
        return True
    until = item.get("until")
    if until:
        try:
            if datetime.fromisoformat(until) > datetime.now():
                return True
            del banned[str(user_id)]
            save_banned(banned)
        except Exception:
            return True
    return False

def create_user(user_id, ref_by=0):
    users = load_users()
    uid = str(user_id)
    if uid in users:
        return users[uid]

    user = {
        "balance": 50000,
        "ref_code": generate_ref_code(),
        "ref_by": str(ref_by),
        "invite_count": 0,
        "subscription_type": "عادی",
        "subscription_expire": None,
        "reg_date": datetime.now().isoformat(),
    }
    users[uid] = user

    if ref_by and str(ref_by) in users and str(ref_by) != uid:
        users[str(ref_by)]["balance"] = int(users[str(ref_by)].get("balance", 0)) + 50000
        users[str(ref_by)]["invite_count"] = int(users[str(ref_by)].get("invite_count", 0)) + 1

    save_users(users)

    if ref_by and str(ref_by) in users and str(ref_by) != uid:
        add_invite(ref_by, user_id)
        send_message(ref_by, "🎁 ۵۰,۰۰۰ تومان جایزه دعوت به حساب شما واریز شد!")
        send_message(ref_by, f"🎯 کاربر جدید با آیدی `{user_id}` وارد شد.")

    return user

def add_invite(ref_by, new_user_id):
    invites = load_invites()
    key = str(ref_by)
    if key not in invites:
        invites[key] = {"invites": []}
    if not any(str(x.get("user_id")) == str(new_user_id) for x in invites[key]["invites"]):
        invites[key]["invites"].append({
            "user_id": int(new_user_id),
            "time": datetime.now().isoformat()
        })
        save_invites(invites)

def get_invites(user_id):
    return load_invites().get(str(user_id), {}).get("invites", [])

def get_ref_link(ref_code):
    return f"https://t.me/{BOT_USERNAME}?start={ref_code}"

def grant_gold_subscription(user_id, days):
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        return False
    current = datetime.now()
    old = users[uid].get("subscription_expire")
    if old:
        try:
            old_dt = datetime.fromisoformat(old)
            if old_dt > current:
                current = old_dt
        except Exception:
            pass
    users[uid]["subscription_type"] = "طلایی"
    users[uid]["subscription_expire"] = (current + timedelta(days=days)).isoformat()
    save_users(users)
    send_message(user_id, f"🎉 اشتراک طلایی شما برای {days} روز فعال شد!")
    return True

# ---------------- Telegram ----------------

def telegram(method, payload):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/{method}"
        r = requests.post(url, json=payload, timeout=15)
        return r.status_code == 200, r.json()
    except Exception as e:
        print(f"Telegram {method}: {e}")
        return False, {}

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    ok, _ = telegram("sendMessage", payload)
    return ok

def answer_callback(callback_id):
    telegram("answerCallbackQuery", {"callback_query_id": callback_id})

# ---------------- Keyboards ----------------

def main_keyboard():
    return {"keyboard": [
        [{"text": "🎯 سوژه ها"}, {"text": "💎 خرید طلایی"}],
        [{"text": "📖 راهنما"}, {"text": "📊 پروفایل"}],
        [{"text": "📞 پشتیبانی"}]
    ], "resize_keyboard": True}

def admin_keyboard():
    return {"keyboard": [
        [{"text": "📊 آمار کاربران"}, {"text": "🚫 مسدود کردن کاربر"}],
        [{"text": "🎁 اعطای اشتراک طلایی"}, {"text": "📩 تیکت‌ها"}],
        [{"text": "📢 اطلاع‌رسانی"}, {"text": "🔄 ریست کاربران عادی"}],
        [{"text": "🔒 مسدود کردن دریافت پیام"}, {"text": "⚙️ تنظیمات"}],
        [{"text": "👤 رفتن به صفحه کاربر عادی"}],
    ], "resize_keyboard": True}

def user_mode_keyboard():
    return {"keyboard": [
        [{"text": "🎯 سوژه ها"}, {"text": "💎 خرید طلایی"}],
        [{"text": "📖 راهنما"}, {"text": "📊 پروفایل"}],
        [{"text": "📞 پشتیبانی"}],
        [{"text": "👑 بازگشت به پنل ادمین"}],
    ], "resize_keyboard": True}

def back_keyboard():
    return {"keyboard": [[{"text": "🔙 بازگشت"}]], "resize_keyboard": True}

def gold_keyboard():
    return {"inline_keyboard": [
        [{"text": "💎 ۷ روزه - ۵۰,۰۰۰ تومان", "callback_data": "gold_7"}],
        [{"text": "💎 ۱۴ روزه - ۱۰۰,۰۰۰ تومان", "callback_data": "gold_14"}],
        [{"text": "💎 یکماهه - ۱۲۰,۰۰۰ تومان", "callback_data": "gold_30"}],
        [{"text": "🔙 بازگشت", "callback_data": "back_main"}],
    ]}

def confirm_keyboard():
    return {"inline_keyboard": [
        [{"text": "✅ تایید", "callback_data": "reset_confirm"}],
        [{"text": "❌ لغو", "callback_data": "reset_cancel"}],
    ]}

# ---------------- Text ----------------

def profile_text(user_id):
    user = get_user(user_id)
    if not user:
        return "❌ کاربر یافت نشد."
    sub = user.get("subscription_type", "عادی")
    expire = user.get("subscription_expire")
    text = (
        "👤 پروفایل کاربری\n\n"
        f"🆔 شناسه: {user_id}\n"
        f"💰 موجودی: {int(user.get('balance', 0)):,} تومان\n"
        f"👥 دعوت‌شده‌ها: {user.get('invite_count', 0)} نفر\n"
        f"📊 اشتراک: {sub}\n\n"
        f"🔗 لینک دعوت:\n{get_ref_link(user.get('ref_code', ''))}"
    )
    if sub == "طلایی" and expire:
        try:
            remaining = datetime.fromisoformat(expire) - datetime.now()
            if remaining.total_seconds() > 0:
                text += f"\n\n⏳ باقی‌مانده: {remaining.days} روز و {remaining.seconds // 3600} ساعت"
        except Exception:
            pass
    return text

def help_text():
    return """📖 راهنمای ربات

🎯 این ربات برای شوخی و سرگرمی بین دوستان طراحی شده است.

🔹 از پروفایل، لینک دعوت خود را دریافت کنید.
🔹 کاربران دعوت‌شده در بخش «سوژه‌ها» نمایش داده می‌شوند.
🔹 می‌توانید پیام خود را برای یک کاربر دعوت‌شده ارسال کنید.

💎 اشتراک طلایی:
• امکانات بیشتر
• محدودیت‌های بیشتر برای متن و استفاده
• پشتیبانی اختصاصی

📞 برای مشکل یا سؤال از بخش پشتیبانی استفاده کنید."""

# ---------------- User features ----------------

def show_invites(user_id):
    invites = get_invites(user_id)
    if not invites:
        send_message(user_id, "❌ هنوز کسی را دعوت نکرده‌اید.", main_keyboard())
        return
    lines = ["📋 سوژه‌های شما:\n"]
    for i, item in enumerate(invites, 1):
        lines.append(f"{i}. 🆔 {item.get('user_id')} - {item.get('time', '')[:16]}")
    lines.append("\n🔢 شماره سوژه را ارسال کنید.")
    send_message(user_id, "\n".join(lines), {
        "keyboard": [[{"text": "🔙 بازگشت"}], [{"text": "🏠 منو اصلی"}]],
        "resize_keyboard": True
    })
    save_user_setting(user_id, "state", "invite_number")

def send_single_message(user_id, target_id, text):
    if is_blocked(target_id):
        send_message(user_id, "❌ این کاربر دریافت پیام را مسدود کرده است.", main_keyboard())
        return
    if len(text.splitlines()) > 5:
        send_message(user_id, "❌ پیام کاربران عادی حداکثر ۵ خط است.", main_keyboard())
        return
    if len(text) > 4000:
        send_message(user_id, "❌ پیام بیش از حد طولانی است.", main_keyboard())
        return
    if send_message(target_id, f"💬 پیام دوستت:\n\n{text}"):
        send_message(user_id, "✅ پیام ارسال شد.", main_keyboard())
    else:
        send_message(user_id, "❌ ارسال پیام انجام نشد.", main_keyboard())

def reset_normal_users():
    users = load_users()
    invites = load_invites()
    for uid, data in users.items():
        if data.get("subscription_type") != "طلایی":
            data["balance"] = 50000
            data["invite_count"] = 0
            data["ref_code"] = generate_ref_code()
            invites.pop(uid, None)
    save_users(users)
    save_invites(invites)

# ---------------- Callbacks ----------------

def process_callback(cb):
    callback_id = cb.get("id")
    answer_callback(callback_id)
    data = cb.get("data", "")
    chat_id = cb["message"]["chat"]["id"]
    user_id = int(chat_id)

    if data == "back_main":
        send_message(user_id, profile_text(user_id), main_keyboard())
        return

    if data.startswith("gold_"):
        plan_id = data.split("_", 1)[1]
        plan = GOLD_PLANS.get(plan_id)
        if not plan:
            return
        requests_db = load_gold_requests()
        uid = str(user_id)
        if uid in requests_db and requests_db[uid].get("status") == "pending":
            send_message(user_id, "❌ شما یک درخواست در انتظار دارید.", main_keyboard())
            return
        requests_db[uid] = {
            "user_id": user_id,
            "plan": plan["name"],
            "days": plan["days"],
            "price": plan["price"],
            "status": "pending",
            "time": datetime.now().isoformat()
        }
        save_gold_requests(requests_db)
        send_message(user_id, "✅ درخواست اشتراک ثبت شد. منتظر بررسی ادمین باشید.", main_keyboard())
        send_message(ADMIN_ID, f"📩 درخواست اشتراک طلایی\n🆔 {user_id}\n📦 {plan['name']}\n💰 {plan['price']:,} تومان")
        return

    if data == "reset_confirm" and is_admin(user_id):
        reset_normal_users()
        send_message(user_id, "✅ اطلاعات کاربران عادی ریست شد.", admin_keyboard())
    elif data == "reset_cancel" and is_admin(user_id):
        send_message(user_id, "❌ لغو شد.", admin_keyboard())

# ---------------- Messages ----------------

def process_message(msg):
    chat_id = msg["chat"]["id"]
    user_id = int(msg["from"]["id"])
    text = msg.get("text", "")

    if is_banned(user_id):
        send_message(chat_id, "🚫 شما مسدود شده‌اید.")
        return

    # Admin mode is stored per-admin; default is admin.
    admin_mode = get_user_settings(ADMIN_ID).get("admin_mode", True) if is_admin(user_id) else False

    if text.startswith("/start"):
        ref_by = 0
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            code = parts[1].strip()
            for uid, data in load_users().items():
                if data.get("ref_code") == code:
                    ref_by = int(uid)
                    break
        user = get_user(user_id)
        if not user:
            create_user(user_id, ref_by)
            user = get_user(user_id)
        if is_admin(user_id) and admin_mode:
            send_message(chat_id, "👑 پنل ادمین", admin_keyboard())
        else:
            send_message(chat_id, profile_text(user_id), user_mode_keyboard() if is_admin(user_id) else main_keyboard())
        return

    if is_admin(user_id):
        if text == "👤 رفتن به صفحه کاربر عادی":
            save_user_setting(ADMIN_ID, "admin_mode", False)
            send_message(chat_id, "👤 اکنون در حالت کاربر عادی هستید.", user_mode_keyboard())
            send_message(chat_id, profile_text(user_id))
            return
        if text == "👑 بازگشت به پنل ادمین":
            save_user_setting(ADMIN_ID, "admin_mode", True)
            save_user_setting(ADMIN_ID, "state", None)
            send_message(chat_id, "👑 به پنل ادمین برگشتید.", admin_keyboard())
            return

    # If admin is in normal-user mode, process normal features only.
    if is_admin(user_id) and not admin_mode:
        process_normal_message(user_id, text, True)
        return

    # Admin panel
    if is_admin(user_id) and admin_mode:
        if text == "📊 آمار کاربران":
            users = load_users()
            gold = sum(1 for x in users.values() if x.get("subscription_type") == "طلایی")
            send_message(chat_id, f"📊 آمار کاربران\n\n👥 کل: {len(users)}\n🟢 عادی: {len(users)-gold}\n🟡 طلایی: {gold}\n🚫 بن: {len(load_banned())}\n🔒 بلاک دریافت پیام: {len(load_blocked())}", admin_keyboard())
            return
        if text == "🎁 اعطای اشتراک طلایی":
            send_message(chat_id, "🆔 آیدی کاربر را ارسال کنید.", back_keyboard())
            save_user_setting(ADMIN_ID, "state", "grant_gold")
            return
        if text == "🚫 مسدود کردن کاربر":
            send_message(chat_id, "🆔 آیدی کاربر را ارسال کنید.", back_keyboard())
            save_user_setting(ADMIN_ID, "state", "ban")
            return
        if text == "🔒 مسدود کردن دریافت پیام":
            send_message(chat_id, "🆔 آیدی کاربر را ارسال کنید.", back_keyboard())
            save_user_setting(ADMIN_ID, "state", "block")
            return
        if text == "🔄 ریست کاربران عادی":
            send_message(chat_id, "⚠️ مطمئن هستید؟", confirm_keyboard())
            return
        if text == "📩 تیکت‌ها":
            pending = [x for x in load_tickets().values() if x.get("status") == "pending"]
            if not pending:
                send_message(chat_id, "✅ تیکت در انتظار وجود ندارد.", admin_keyboard())
            else:
                for t in pending[:10]:
                    send_message(chat_id, f"📩 تیکت\n🆔 {t.get('user_id')}\n\n{t.get('message')}", admin_keyboard())
            return
        if text == "📢 اطلاع‌رسانی":
            send_message(chat_id, "📝 متن اطلاعیه را ارسال کنید.", back_keyboard())
            save_user_setting(ADMIN_ID, "state", "broadcast")
            return
        if text == "⚙️ تنظیمات":
            send_message(chat_id, "⚙️ تنظیمات فعلاً شامل حالت نمایش پنل و کاربر عادی است.", admin_keyboard())
            return
        if text == "🔙 بازگشت":
            save_user_setting(ADMIN_ID, "state", None)
            send_message(chat_id, "👑 پنل ادمین", admin_keyboard())
            return

        state = get_user_settings(ADMIN_ID).get("state")
        if state == "grant_gold":
            if text.isdigit() and get_user(int(text)):
                save_user_setting(ADMIN_ID, "grant_target", int(text))
                send_message(chat_id, "مدت را با یکی از این اعداد ارسال کنید: 7، 14، 30", back_keyboard())
                save_user_setting(ADMIN_ID, "state", "grant_gold_days")
            else:
                send_message(chat_id, "❌ آیدی نامعتبر است.", admin_keyboard())
            return
        if state == "grant_gold_days":
            if text in GOLD_PLANS:
                target = get_user_settings(ADMIN_ID).get("grant_target")
                if target and grant_gold_subscription(target, GOLD_PLANS[text]["days"]):
                    send_message(chat_id, "✅ اشتراک فعال شد.", admin_keyboard())
                save_user_setting(ADMIN_ID, "state", None)
                return
        if state == "ban":
            if text.isdigit() and get_user(int(text)):
                banned = load_banned()
                banned[str(int(text))] = {"type": "permanent"}
                save_banned(banned)
                send_message(chat_id, "🔒 کاربر مسدود شد.", admin_keyboard())
            else:
                send_message(chat_id, "❌ آیدی نامعتبر است.", admin_keyboard())
            save_user_setting(ADMIN_ID, "state", None)
            return
        if state == "block":
            if text.isdigit() and get_user(int(text)):
                blocked = load_blocked()
                blocked[str(int(text))] = {}
                save_blocked(blocked)
                send_message(chat_id, "🔒 دریافت پیام برای کاربر مسدود شد.", admin_keyboard())
            else:
                send_message(chat_id, "❌ آیدی نامعتبر است.", admin_keyboard())
            save_user_setting(ADMIN_ID, "state", None)
            return
        if state == "broadcast":
            if text != "🔙 بازگشت":
                for uid in load_users():
                    if not is_banned(int(uid)):
                        send_message(int(uid), f"📢 اطلاعیه:\n\n{text}")
                        time.sleep(0.05)
                send_message(chat_id, "✅ اطلاعیه ارسال شد.", admin_keyboard())
            save_user_setting(ADMIN_ID, "state", None)
            return

    process_normal_message(user_id, text, False)

def process_normal_message(user_id, text, is_admin_user=False):
    user = get_user(user_id)
    if not user:
        user = create_user(user_id)
    keyboard = user_mode_keyboard() if is_admin_user else main_keyboard()
    state = get_user_settings(user_id).get("state")

    if text == "🏠 منو اصلی":
        send_message(user_id, profile_text(user_id), keyboard)
        return
    if text == "📖 راهنما":
        send_message(user_id, help_text(), keyboard)
        return
    if text == "📊 پروفایل":
        send_message(user_id, profile_text(user_id), keyboard)
        return
    if text == "🎯 سوژه ها":
        show_invites(user_id)
        return
    if text == "💎 خرید طلایی":
        send_message(user_id, "💎 پلن مورد نظر را انتخاب کنید:", gold_keyboard())
        return
    if text == "📞 پشتیبانی":
        send_message(user_id, "📝 مشکل خود را بنویسید.", back_keyboard())
        save_user_setting(user_id, "state", "ticket")
        return

    if state == "invite_number":
        if text == "🔙 بازگشت":
            save_user_setting(user_id, "state", None)
            send_message(user_id, profile_text(user_id), keyboard)
            return
        if text.isdigit():
            n = int(text)
            invites = get_invites(user_id)
            if 1 <= n <= len(invites):
                target = int(invites[n-1]["user_id"])
                save_user_setting(user_id, "pending_target", target)
                save_user_setting(user_id, "state", "message")
                send_message(user_id, "✏️ پیام خود را ارسال کنید (حداکثر ۵ خط):", back_keyboard())
            else:
                send_message(user_id, "❌ شماره اشتباه است.")
        return

    if state == "message":
        if text == "🔙 بازگشت":
            save_user_setting(user_id, "state", None)
            send_message(user_id, profile_text(user_id), keyboard)
            return
        target = get_user_settings(user_id).get("pending_target")
        if target:
            send_single_message(user_id, int(target), text)
        save_user_setting(user_id, "state", None)
        return

    if state == "ticket":
        if text == "🔙 بازگشت":
            save_user_setting(user_id, "state", None)
            send_message(user_id, profile_text(user_id), keyboard)
            return
        tickets = load_tickets()
        ticket_id = str(int(time.time() * 1000))
        tickets[ticket_id] = {
            "user_id": str(user_id),
            "message": text,
            "status": "pending",
            "reply": None,
            "time": datetime.now().isoformat()
        }
        save_tickets(tickets)
        send_message(user_id, "✅ تیکت شما ثبت شد.", keyboard)
        send_message(ADMIN_ID, f"📩 تیکت جدید از {user_id}\n\n{text}", admin_keyboard())
        save_user_setting(user_id, "state", None)
        return

    send_message(user_id, profile_text(user_id), keyboard)

# ---------------- Webhook ----------------

@app.route("/", methods=["GET"])
def index():
    return "ربات روشن است! 🚀"

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json(silent=True) or {}
        if "message" in data:
            process_message(data["message"])
        elif "callback_query" in data:
            process_callback(data["callback_query"])
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"webhook: {e}")
        return jsonify({"status": "error"}), 500

@app.route("/setwebhook", methods=["GET"])
def set_webhook():
    base_url = os.getenv("WEBHOOK_URL", "").rstrip("/")
    if not base_url:
        return jsonify({"error": "WEBHOOK_URL در .env تنظیم نشده است."}), 400
    ok, result = telegram("setWebhook", {"url": base_url + "/"})
    return jsonify(result), 200 if ok else 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
