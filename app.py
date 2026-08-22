from flask import Flask, request, jsonify
import requests
import json
import os
import random
import string
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)

TOKEN = "8958267630:AAFIo-Q8XnD0K8hyBRUhhyFetVxasf3Uv_4"
BOT_USERNAME = "POOLREGBARR_BOT"
ADMIN_ID = 8235703809
PROTECTED_USERS = [ADMIN_ID]

DB_FILE = "pool_regbar_users.json"
MESSAGES_FILE = "pool_regbar_messages.json"
SETTINGS_FILE = "pool_regbar_settings.json"
TICKETS_FILE = "pool_regbar_tickets.json"
INVITES_FILE = "pool_regbar_invites.json"
GOLD_REQUESTS_FILE = "pool_regbar_gold_requests.json"
BANNED_FILE = "pool_regbar_banned.json"

GOLD_PLANS = {
    "7": {"days": 7, "price": 50000, "name": "۷ روزه"},
    "14": {"days": 14, "price": 100000, "name": "۱۴ روزه"},
    "30": {"days": 30, "price": 120000, "name": "یکماهه"}
}

def load_db(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {}

def save_db(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(url, json=data, timeout=10)
        return True
    except Exception as e:
        print(f"خطا در ارسال: {e}")
        return False

def send_message_to_user(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=data, timeout=10)
        return True
    except Exception as e:
        print(f"خطا در ارسال: {e}")
        return False

def generate_ref_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def get_user(user_id):
    db = load_db(DB_FILE)
    return db.get(str(user_id))

def is_admin(user_id):
    return user_id == ADMIN_ID

def is_banned(user_id):
    banned = load_db(BANNED_FILE)
    return str(user_id) in banned

def is_protected(user_id):
    return user_id in PROTECTED_USERS

def get_user_settings(user_id):
    settings = load_db(SETTINGS_FILE)
    return settings.get(str(user_id), {})

def save_user_setting(user_id, key, value):
    settings = load_db(SETTINGS_FILE)
    user_id_str = str(user_id)
    if user_id_str not in settings:
        settings[user_id_str] = {}
    settings[user_id_str][key] = value
    save_db(SETTINGS_FILE, settings)

def get_user_message(user_id):
    messages = load_db(MESSAGES_FILE)
    return messages.get(str(user_id))

def save_user_message(user_id, message):
    messages = load_db(MESSAGES_FILE)
    messages[str(user_id)] = message
    save_db(MESSAGES_FILE, messages)

def get_invites(user_id):
    invites = load_db(INVITES_FILE)
    return invites.get(str(user_id), [])

def add_invite(ref_by, new_user_id):
    try:
        invites = load_db(INVITES_FILE)
        ref_by_str = str(ref_by)
        if ref_by_str not in invites:
            invites[ref_by_str] = []
        
        # چک کن که کاربر قبلاً دعوت نشده باشه
        existing = [inv for inv in invites[ref_by_str] if inv.get("user_id") == new_user_id]
        if not existing:
            invites[ref_by_str].append({
                "user_id": new_user_id,
                "time": datetime.now().isoformat()
            })
            save_db(INVITES_FILE, invites)
            print(f"✅ دعوت ثبت شد: {ref_by} -> {new_user_id}")
            return True
        else:
            print(f"⚠️ کاربر {new_user_id} قبلاً توسط {ref_by} دعوت شده")
            return False
    except Exception as e:
        print(f"❌ خطا در add_invite: {e}")
        return False

def create_user(user_id, ref_by=0):
    db = load_db(DB_FILE)
    user_id_str = str(user_id)
    if user_id_str in db:
        return db[user_id_str]
    ref_code = generate_ref_code()
    now = datetime.now().isoformat()
    db[user_id_str] = {
        "user_id": user_id,
        "balance": 50000,
        "ref_code": ref_code,
        "ref_by": ref_by,
        "invite_count": 0,
        "subscription_type": "عادی",
        "subscription_expire": None,
        "reg_date": now
    }
    save_db(DB_FILE, db)
    
    if ref_by != 0:
        ref_by_str = str(ref_by)
        if ref_by_str in db:
            db[ref_by_str]["balance"] += 50000
            db[ref_by_str]["invite_count"] += 1
            save_db(DB_FILE, db)
            
            send_message(ref_by, "🎁 ۵۰,۰۰۰ تومان جایزه دعوت به حساب شما واریز شد!")
            
            add_invite(ref_by, user_id)
            
            send_new_user_notification(ref_by, user_id)
    
    return db[user_id_str]

def get_ref_link(ref_code):
    return f"https://t.me/{BOT_USERNAME}?start={ref_code}"

def grant_gold_subscription(user_id, days):
    db = load_db(DB_FILE)
    user_id_str = str(user_id)
    if user_id_str not in db:
        return False
    expire_date = (datetime.now() + timedelta(days=days)).isoformat()
    db[user_id_str]["subscription_type"] = "طلایی"
    db[user_id_str]["subscription_expire"] = expire_date
    save_db(DB_FILE, db)
    if user_id not in PROTECTED_USERS:
        PROTECTED_USERS.append(user_id)
    send_message(user_id, f"🎉 **تبریک! اشتراک طلایی شما فعال شد!**\n📦 مدت: {days} روز\n📅 تا تاریخ: {expire_date[:10]}")
    return True

def get_user_stats():
    db = load_db(DB_FILE)
    total = len(db)
    gold = sum(1 for u in db.values() if u.get("subscription_type") == "طلایی")
    normal = total - gold
    banned = len(load_db(BANNED_FILE))
    return total, normal, gold, banned

def reset_normal_users():
    db = load_db(DB_FILE)
    invites = load_db(INVITES_FILE)
    for uid, data in db.items():
        if data.get("subscription_type") != "طلایی":
            data["balance"] = 50000
            data["invite_count"] = 0
            data["ref_code"] = generate_ref_code()
            if uid in invites:
                invites[uid] = []
    save_db(DB_FILE, db)
    save_db(INVITES_FILE, invites)
    return True

def get_notification_keyboard(ref_by, new_user_id):
    return {
        "inline_keyboard": [
            [{"text": "✏️ تنظیم پیام", "callback_data": f"set_msg_{ref_by}"},
             {"text": "🔢 تعداد پیام", "callback_data": f"set_count_{ref_by}"}],
            [{"text": "✅ تایید و ارسال", "callback_data": f"send_msg_{ref_by}_{new_user_id}"}]
        ]
    }

def get_count_keyboard(ref_by):
    return {
        "inline_keyboard": [
            [{"text": "۱۰ پیام", "callback_data": f"count_{ref_by}_10"}],
            [{"text": "۵۰ پیام", "callback_data": f"count_{ref_by}_50"}],
            [{"text": "۱۰۰ پیام", "callback_data": f"count_{ref_by}_100"}],
            [{"text": "۲۰۰ پیام", "callback_data": f"count_{ref_by}_200"}],
            [{"text": "۴۰۰ پیام", "callback_data": f"count_{ref_by}_400"}],
            [{"text": "۸۰۰ پیام", "callback_data": f"count_{ref_by}_800"}],
            [{"text": "۱۶۰۰ پیام", "callback_data": f"count_{ref_by}_1600"}],
            [{"text": "۳۲۰۰ پیام", "callback_data": f"count_{ref_by}_3200"}]
        ]
    }

def get_confirm_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "✏️ تنظیم دوباره", "callback_data": "edit_message"},
             {"text": "✅ بله", "callback_data": "confirm_message"}]
        ]
    }

def get_admin_keyboard():
    return {
        "keyboard": [
            [{"text": "📊 آمار کاربران"}, {"text": "🚫 مسدود کردن کاربر"}],
            [{"text": "🎁 اعطای اشتراک طلایی"}, {"text": "📩 تیکت‌ها"}],
            [{"text": "📢 اطلاع‌رسانی"}, {"text": "🔄 ریست اطلاعات کاربران عادی"}],
            [{"text": "⚙️ تنظیمات"}, {"text": "🏠 منو اصلی"}]
        ],
        "resize_keyboard": True
    }

def get_ticket_keyboard(ticket_id):
    return {
        "inline_keyboard": [
            [{"text": "📝 پاسخ", "callback_data": f"ticket_reply_{ticket_id}"}],
            [{"text": "✅ پاسخ داده شد", "callback_data": f"ticket_done_{ticket_id}"}]
        ]
    }

def get_back_keyboard():
    return {"keyboard": [[{"text": "🔙 بازگشت"}]], "resize_keyboard": True}

def get_gold_plans_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🎁 ۷ روزه", "callback_data": "admin_gold_7"}],
            [{"text": "🎁 ۱۴ روزه", "callback_data": "admin_gold_14"}],
            [{"text": "🎁 یکماهه", "callback_data": "admin_gold_30"}],
            [{"text": "🔙 بازگشت", "callback_data": "back_to_admin"}]
        ]
    }

def get_reset_confirm_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "✅ تایید", "callback_data": "reset_confirm"}],
            [{"text": "❌ لغو", "callback_data": "reset_cancel"}]
        ]
    }

def get_gold_request_keyboard(user_id, days):
    return {
        "inline_keyboard": [
            [{"text": "💬 ارسال پیام به کاربر", "callback_data": f"msg_to_user_{user_id}"}],
            [{"text": "✅ فعال‌سازی اشتراک", "callback_data": f"admin_approve_gold_{user_id}_{days}"}]
        ]
    }

def get_reply_confirm_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "✅ تایید و ارسال", "callback_data": "reply_confirm"}],
            [{"text": "❌ لغو", "callback_data": "reply_cancel"}]
        ]
    }

def get_ban_days_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "۱ روز", "callback_data": "ban_1"}],
            [{"text": "۳ روز", "callback_data": "ban_3"}],
            [{"text": "۷ روز", "callback_data": "ban_7"}],
            [{"text": "۱۴ روز", "callback_data": "ban_14"}],
            [{"text": "۳۰ روز", "callback_data": "ban_30"}],
            [{"text": "🔒 دائمی", "callback_data": "ban_permanent"}],
            [{"text": "🔙 بازگشت", "callback_data": "back_to_admin"}]
        ]
    }

def main_keyboard():
    return {
        "keyboard": [
            [{"text": "🎯 سوژه ها"}, {"text": "💎 خرید طلایی"}],
            [{"text": "📞 پشتیبانی"}, {"text": "📊 پروفایل"}]
        ],
        "resize_keyboard": True
    }

def profile_keyboard(ref_code, user_id):
    return {
        "inline_keyboard": [
            [{"text": "📋 کپی لینک دعوت", "callback_data": f"copy_link_{ref_code}"},
             {"text": "🆔 کپی آیدی عددی", "callback_data": f"copy_id_{user_id}"}]
        ]
    }

def show_invite_list(user_id):
    invites = get_invites(user_id)
    if not invites:
        send_message(user_id, "❌ شما هنوز کسی را دعوت نکرده‌اید!", main_keyboard())
        return
    text = "📋 **لیست دعوت‌شده‌ها:**\n\n"
    for i, inv in enumerate(invites, 1):
        text += f"{i}. 🆔 {inv['user_id']} - 🕐 {inv['time'][:16]}\n"
    text += "\n🔢 **عدد مورد نظر را ارسال کنید:**"
    send_message(user_id, text, {
        "keyboard": [[{"text": "🔙 بازگشت"}], [{"text": "🏠 منو اصلی"}]],
        "resize_keyboard": True
    })
    save_user_setting(user_id, "state", "waiting_for_invite_number")
    save_user_setting(user_id, "real_invites", invites)

def profile_text(user):
    if not user:
        return "❌ کاربر یافت نشد!"
    balance = user.get("balance", 0)
    invite_count = user.get("invite_count", 0)
    sub_type = user.get("subscription_type", "عادی")
    ref_code = user.get("ref_code", "")
    user_id = user.get("user_id", 0)
    sub_expire = user.get("subscription_expire")
    text = f"""👤 **پروفایل کاربری**

🆔 شناسه: `{user_id}`
💰 موجودی: {balance:,} تومان
👥 دعوت شده‌ها: {invite_count} نفر
📊 نوع اشتراک: {sub_type}

🔗 لینک دعوت:
`{get_ref_link(ref_code)}`
"""
    if sub_type == "طلایی" and sub_expire:
        try:
            expire_time = datetime.fromisoformat(sub_expire)
            remaining = expire_time - datetime.now()
            days = remaining.days
            hours = remaining.seconds // 3600
            if days >= 0:
                text += f"\n⏳ زمان باقی‌مانده: {days} روز و {hours} ساعت"
        except:
            pass
    return text

def send_new_user_notification(ref_by, new_user_id):
    if is_protected(new_user_id):
        send_message(ref_by, f"❌ **ارسال پیام به این کاربر امکان پذیر نیست!**\n🆔 کاربر: `{new_user_id}`\nاین کاربر دارای اشتراک **طلایی** می‌باشد.", main_keyboard())
        return
    message = f"""🎯 **سوژه جدید وارد شد!**

🆔 کاربر: `{new_user_id}`

از دکمه‌های زیر استفاده کنید:"""
    send_message(ref_by, message, get_notification_keyboard(ref_by, new_user_id))

def show_invite_message(user_id):
    settings = get_user_settings(user_id)
    new_user_id = settings.get("pending_new_user")
    if new_user_id:
        send_new_user_notification(user_id, new_user_id)
    else:
        user = get_user(user_id)
        if user:
            send_message(user_id, profile_text(user), main_keyboard())

def process_callback(callback):
    chat_id = str(callback["message"]["chat"]["id"])
    user_id = int(chat_id)
    data = callback["data"]
    
    if data.startswith("copy_link_"):
        ref_code = data.replace("copy_link_", "")
        link = get_ref_link(ref_code)
        send_message(chat_id, f"📋 **لینک دعوت:**\n\n`{link}`", {"keyboard": [[{"text": "📊 پروفایل"}]], "resize_keyboard": True})
    elif data.startswith("copy_id_"):
        user_id_data = data.replace("copy_id_", "")
        send_message(chat_id, f"🆔 **آیدی شما:**\n\n`{user_id_data}`", {"keyboard": [[{"text": "📊 پروفایل"}]], "resize_keyboard": True})
    elif data == "buy_gold":
        send_message(chat_id, "💎 **انتخاب اشتراک:**", get_gold_plans_keyboard())
    elif data.startswith("gold_plan_"):
        days = data.replace("gold_plan_", "")
        if days in GOLD_PLANS:
            plan = GOLD_PLANS[days]
            requests_db = load_db(GOLD_REQUESTS_FILE)
            if str(user_id) in requests_db:
                send_message(chat_id, "❌ قبلاً درخواست ثبت کردی!", main_keyboard())
                return
            requests_db[str(user_id)] = {
                "user_id": user_id,
                "plan": plan["name"],
                "days": plan["days"],
                "price": plan["price"],
                "status": "pending",
                "time": datetime.now().isoformat()
            }
            save_db(GOLD_REQUESTS_FILE, requests_db)
            send_message(chat_id, f"✅ درخواست ثبت شد!\n📦 {plan['name']}\n💰 {plan['price']:,} تومان", main_keyboard())
            send_message(ADMIN_ID, f"📩 درخواست طلایی!\n🆔 {user_id}\n📦 {plan['name']}\n💰 {plan['price']:,}", get_gold_request_keyboard(user_id, plan['days']))
    elif data.startswith("msg_to_user_"):
        if not is_admin(user_id):
            return
        target_user = int(data.replace("msg_to_user_", ""))
        save_user_setting(ADMIN_ID, "gold_msg_target", target_user)
        send_message(chat_id, "💬 پیامت رو بنویس:", get_back_keyboard())
        save_user_setting(ADMIN_ID, "state", "admin_gold_message")
    elif data.startswith("admin_approve_gold_"):
        if not is_admin(user_id):
            return
        parts = data.split("_")
        target_user = int(parts[3])
        days = int(parts[4])
        if grant_gold_subscription(target_user, days):
            send_message(chat_id, f"✅ اشتراک {days} روزه به {target_user} اعطا شد!", get_admin_keyboard())
        else:
            send_message(chat_id, "❌ خطا!", get_admin_keyboard())
    elif data.startswith("admin_gold_"):
        if not is_admin(user_id):
            return
        days = data.replace("admin_gold_", "")
        target_user = get_user_settings(ADMIN_ID).get("grant_gold_target")
        if target_user and grant_gold_subscription(target_user, int(days)):
            send_message(chat_id, f"✅ اشتراک {days} روزه به {target_user} اعطا شد!", get_admin_keyboard())
        else:
            send_message(chat_id, "❌ خطا!", get_admin_keyboard())
        save_user_setting(ADMIN_ID, "grant_gold_target", None)
    elif data == "reply_confirm":
        if not is_admin(user_id):
            return
        reply_text = get_user_settings(ADMIN_ID).get("reply_text")
        ticket_id = get_user_settings(ADMIN_ID).get("replying_ticket")
        if reply_text and ticket_id:
            tickets = load_db(TICKETS_FILE)
            if ticket_id in tickets:
                ticket = tickets[ticket_id]
                send_message(ticket["user_id"], f"📩 **پاسخ ادمین:**\n\n{reply_text}")
                tickets[ticket_id]["status"] = "answered"
                tickets[ticket_id]["reply"] = reply_text
                save_db(TICKETS_FILE, tickets)
                send_message(chat_id, "✅ پاسخ ارسال شد!", get_admin_keyboard())
                save_user_setting(ADMIN_ID, "reply_text", None)
                save_user_setting(ADMIN_ID, "replying_ticket", None)
                save_user_setting(ADMIN_ID, "state", None)
    elif data == "reply_cancel":
        if not is_admin(user_id):
            return
        save_user_setting(ADMIN_ID, "reply_text", None)
        save_user_setting(ADMIN_ID, "replying_ticket", None)
        save_user_setting(ADMIN_ID, "state", None)
        send_message(chat_id, "❌ لغو شد.", get_admin_keyboard())
    elif data.startswith("ban_"):
        if not is_admin(user_id):
            return
        days_str = data.replace("ban_", "")
        target_user = get_user_settings(ADMIN_ID).get("ban_target")
        if not target_user:
            send_message(chat_id, "❌ خطا!", get_admin_keyboard())
            return
        banned = load_db(BANNED_FILE)
        if days_str == "permanent":
            banned[str(target_user)] = "permanent"
            save_db(BANNED_FILE, banned)
            send_message(chat_id, f"🔒 {target_user} دائمی بن شد!", get_admin_keyboard())
            send_message(target_user, "🚫 **شما دائمی بن شدید!**")
        else:
            days = int(days_str)
            banned[str(target_user)] = {"type": "temporary", "until": (datetime.now() + timedelta(days=days)).isoformat()}
            save_db(BANNED_FILE, banned)
            send_message(chat_id, f"🔒 {target_user} {days} روز بن شد!", get_admin_keyboard())
            send_message(target_user, f"🚫 **شما {days} روز بن شدید!**")
        save_user_setting(ADMIN_ID, "ban_target", None)
        save_user_setting(ADMIN_ID, "state", None)
    elif data.startswith("set_msg_"):
        ref_by = data.replace("set_msg_", "")
        if is_protected(int(ref_by)):
            send_message(chat_id, f"❌ **ارسال پیام به این کاربر امکان پذیر نیست!**\n🆔 کاربر: `{ref_by}`\nاین کاربر دارای اشتراک **طلایی** می‌باشد.", main_keyboard())
            return
        send_message(chat_id, "✏️ پیامت رو بنویس (حداکثر ۵ خط):", {"keyboard": [[{"text": "🔙 بازگشت"}], [{"text": "🏠 منو اصلی"}]], "resize_keyboard": True})
        save_user_setting(user_id, "state", "waiting_for_message")
        save_user_setting(user_id, "ref_by", int(ref_by))
    elif data.startswith("set_count_"):
        ref_by = data.replace("set_count_", "")
        send_message(chat_id, "🔢 تعداد رو انتخاب کن:", get_count_keyboard(ref_by))
    elif data.startswith("count_"):
        parts = data.split("_")
        ref_by = int(parts[1])
        count = int(parts[2])
        user = get_user(user_id)
        is_gold = user and user.get("subscription_type") == "طلایی"
        if not is_gold and count > 50:
            send_message(chat_id, "❌ فقط ۵۰ تا! برای بیشتر طلایی بگیر.", main_keyboard())
            return
        save_user_setting(user_id, "message_count", count)
        save_user_setting(user_id, "ref_by", ref_by)
        send_message(chat_id, f"✅ {count} پیام ذخیره شد.", {"keyboard": [[{"text": "📊 پروفایل"}], [{"text": "🏠 منو اصلی"}]], "resize_keyboard": True})
        time.sleep(0.3)
        show_invite_message(user_id)
    elif data.startswith("send_msg_"):
        parts = data.split("_")
        ref_by = int(parts[2])
        new_user_id = int(parts[3])
        saved_message = get_user_message(user_id)
        message_count = get_user_settings(user_id).get("message_count", 50)
        if not saved_message:
            send_message(chat_id, "❌ پیام تنظیم نشده!", main_keyboard())
            return
        lines = saved_message.count('\n') + 1
        user = get_user(user_id)
        is_gold = user and user.get("subscription_type") == "طلایی"
        if not is_gold and lines > 5:
            send_message(chat_id, "❌ بیش از ۵ خط! طلایی بگیر.", main_keyboard())
            return
        if not is_gold:
            invites = get_invites(user_id)
            if len(invites) >= 15:
                send_message(chat_id, "❌ ۱۵ تا شد! طلایی بگیر.", main_keyboard())
                return
        if is_protected(new_user_id):
            send_message(chat_id, f"❌ **ارسال پیام به این کاربر امکان پذیر نیست!**\n🆔 کاربر: `{new_user_id}`\nاین کاربر دارای اشتراک **طلایی** می‌باشد.", main_keyboard())
            return
        send_message(chat_id, f"⏳ ارسال {message_count} پیام...", main_keyboard())
        
        def send_messages():
            sent_count = 0
            is_sender_gold = user and user.get("subscription_type") == "طلایی"
            for i in range(message_count):
                send_message_to_user(new_user_id, saved_message)
                sent_count += 1
                if not is_sender_gold:
                    time.sleep(2)
                else:
                    time.sleep(0.001)
            send_message(chat_id, f"✅ {sent_count} پیام به {new_user_id} ارسال شد!", main_keyboard())
            time.sleep(0.5)
            show_invite_message(user_id)
        
        thread = threading.Thread(target=send_messages)
        thread.daemon = True
        thread.start()
    elif data == "confirm_message":
        send_message(chat_id, "✅ تایید شد.", {"keyboard": [[{"text": "📊 پروفایل"}], [{"text": "🏠 منو اصلی"}]], "resize_keyboard": True})
        time.sleep(0.3)
        show_invite_message(user_id)
    elif data == "edit_message":
        send_message(chat_id, "✏️ پیام جدیدت رو بنویس:", {"keyboard": [[{"text": "🔙 بازگشت"}], [{"text": "🏠 منو اصلی"}]], "resize_keyboard": True})
        save_user_setting(user_id, "state", "editing_message")
    elif data.startswith("ticket_done_"):
        if not is_admin(user_id):
            return
        ticket_id = data.replace("ticket_done_", "")
        tickets = load_db(TICKETS_FILE)
        if ticket_id in tickets:
            tickets[ticket_id]["status"] = "answered"
            save_db(TICKETS_FILE, tickets)
            send_message(chat_id, "✅ تیکت بسته شد.", get_admin_keyboard())
    elif data.startswith("ticket_reply_"):
        if not is_admin(user_id):
            return
        ticket_id = data.replace("ticket_reply_", "")
        save_user_setting(ADMIN_ID, "replying_ticket", ticket_id)
        send_message(chat_id, "📝 پاسخ رو بنویس:", get_back_keyboard())
        save_user_setting(ADMIN_ID, "state", "admin_ticket_reply")
    elif data == "reset_confirm":
        if not is_admin(user_id):
            return
        reset_normal_users()
        send_message(chat_id, "✅ ریست شد!", get_admin_keyboard())
    elif data == "reset_cancel":
        if not is_admin(user_id):
            return
        send_message(chat_id, "❌ لغو شد.", get_admin_keyboard())
    elif data == "back_to_main":
        user = get_user(user_id)
        if user:
            send_message(chat_id, profile_text(user), main_keyboard())
    elif data == "back_to_admin":
        if is_admin(user_id):
            send_message(chat_id, "👋 پنل ادمین", get_admin_keyboard())

def process_message(msg):
    chat_id = str(msg["chat"]["id"])
    user_id = msg["from"]["id"]
    text = msg.get("text", "")
    
    print(f"📩 پیام از {user_id}: {text[:30] if text else '(غیرمتنی)'}")
    
    if is_banned(user_id):
        send_message(chat_id, "🚫 بن شدی!")
        return
    
    if text.startswith("/activate_gold") and is_admin(user_id):
        parts = text.split()
        if len(parts) == 3:
            try:
                target_user = int(parts[1])
                days = int(parts[2])
                if days in [7, 14, 30] and grant_gold_subscription(target_user, days):
                    send_message(chat_id, f"✅ اشتراک {days} روزه به {target_user} اعطا شد!", get_admin_keyboard())
                else:
                    send_message(chat_id, "❌ خطا!", get_admin_keyboard())
            except:
                send_message(chat_id, "❌ فرمت: /activate_gold [id] [days]", get_admin_keyboard())
        else:
            send_message(chat_id, "❌ فرمت: /activate_gold [id] [days]", get_admin_keyboard())
        return
    
    if text == "🏠 منو اصلی":
        user = get_user(user_id)
        if user:
            if is_admin(user_id):
                send_message(chat_id, "👋 پنل ادمین", get_admin_keyboard())
            else:
                send_message(chat_id, profile_text(user), main_keyboard())
        else:
            send_message(chat_id, "❌ /start بزن", main_keyboard())
        return
    
    if text and (text.startswith("/start") or text == "شروع"):
        ref_by = 0
        ref_code = None
        if " " in text and text.startswith("/start"):
            parts = text.split(" ", 1)
            if len(parts) > 1:
                ref_code = parts[1].strip()
                print(f"🔍 کد دعوت دریافت شد: {ref_code}")
                db = load_db(DB_FILE)
                for uid, data in db.items():
                    if data.get("ref_code") == ref_code:
                        ref_by = int(uid)
                        print(f"✅ دعوت‌کننده پیدا شد: {ref_by}")
                        break
                if ref_by == 0:
                    print(f"⚠️ کد دعوت {ref_code} پیدا نشد!")
        
        user = get_user(user_id)
        if not user:
            print(f"👤 کاربر جدید: {user_id} با دعوت‌کننده: {ref_by}")
            user = create_user(user_id, ref_by)
            send_message(chat_id, f"""🌟 به ربات خوش آمدی!\n🎁 ۵۰,۰۰۰ تومان جایزه ثبت‌نام!\n💫 هر دعوت ۵۰,۰۰۰ تومان!\nاز دکمه‌ها استفاده کن:""", main_keyboard())
        else:
            if is_admin(user_id):
                send_message(chat_id, "👋 پنل ادمین", get_admin_keyboard())
            else:
                send_message(chat_id, profile_text(user), profile_keyboard(user.get("ref_code", ""), user_id))
        return
    
    if is_admin(user_id):
        if text == "📊 آمار کاربران":
            total, normal, gold, banned = get_user_stats()
            send_message(chat_id, f"📊 آمار:\n👥 {total}\n🟢 عادی {normal}\n🟡 طلایی {gold}\n🚫 بن {banned}", get_admin_keyboard())
            return
        elif text == "🚫 مسدود کردن کاربر":
            send_message(chat_id, "🆔 آیدی کاربر رو بفرست:", get_back_keyboard())
            save_user_setting(ADMIN_ID, "state", "admin_ban_user")
            return
        elif text == "🎁 اعطای اشتراک طلایی":
            send_message(chat_id, "🆔 آیدی کاربر رو بفرست:", get_back_keyboard())
            save_user_setting(ADMIN_ID, "state", "admin_grant_gold")
            return
        elif text == "📩 تیکت‌ها":
            tickets = load_db(TICKETS_FILE)
            pending = [t for t in tickets.values() if t.get("status") == "pending"]
            if not pending:
                send_message(chat_id, "✅ تیکتی نیست.", get_admin_keyboard())
                return
            for t in pending[:5]:
                send_message(chat_id, f"📩 تیکت:\n🆔 {t['user_id']}\n📝 {t['message'][:50]}", get_ticket_keyboard(t['id']))
            return
        elif text == "📢 اطلاع‌رسانی":
            send_message(chat_id, "📝 پیام اطلاع‌رسانی رو بنویس:", get_back_keyboard())
            save_user_setting(ADMIN_ID, "state", "admin_broadcast")
            return
        elif text == "🔄 ریست اطلاعات کاربران عادی":
            send_message(chat_id, "⚠️ مطمئنی؟", get_reset_confirm_keyboard())
            return
        elif text == "⚙️ تنظیمات":
            send_message(chat_id, "⚙️ تنظیمات ربات", get_admin_keyboard())
            return
        elif text == "🔙 بازگشت":
            save_user_setting(ADMIN_ID, "state", None)
            send_message(chat_id, "🔙 برگشتی.", get_admin_keyboard())
            return
    
    admin_state = get_user_settings(ADMIN_ID).get("state")
    
    if admin_state == "admin_gold_message" and is_admin(user_id):
        if text == "🔙 بازگشت":
            save_user_setting(ADMIN_ID, "state", None)
            send_message(chat_id, "🔙 برگشتی.", get_admin_keyboard())
            return
        target_user = get_user_settings(ADMIN_ID).get("gold_msg_target")
        if target_user:
            send_message(target_user, f"💬 **پیام ادمین:**\n\n{text}")
            send_message(chat_id, f"✅ ارسال شد!", get_admin_keyboard())
            save_user_setting(ADMIN_ID, "state", None)
            save_user_setting(ADMIN_ID, "gold_msg_target", None)
        return
    
    if admin_state == "admin_ticket_reply" and is_admin(user_id):
        if text == "🔙 بازگشت":
            save_user_setting(ADMIN_ID, "state", None)
            save_user_setting(ADMIN_ID, "replying_ticket", None)
            send_message(chat_id, "🔙 برگشتی.", get_admin_keyboard())
            return
        save_user_setting(ADMIN_ID, "reply_text", text)
        send_message(chat_id, f"📝 پاسخ:\n{text}\nتایید یا لغو؟", get_reply_confirm_keyboard())
        return
    
    if admin_state == "admin_ban_user" and is_admin(user_id):
        if text.isdigit():
            target_user = int(text)
            save_user_setting(ADMIN_ID, "ban_target", target_user)
            send_message(chat_id, f"🔒 مدت بن برای {target_user}:", get_ban_days_keyboard())
            save_user_setting(ADMIN_ID, "state", None)
        else:
            send_message(chat_id, "❌ عدد بفرست!", get_admin_keyboard())
        return
    
    if admin_state == "admin_grant_gold" and is_admin(user_id):
        if text.isdigit():
            target_user = int(text)
            save_user_setting(ADMIN_ID, "grant_gold_target", target_user)
            send_message(chat_id, f"🎁 مدت اشتراک برای {target_user}:", get_admin_gold_plans_keyboard())
            save_user_setting(ADMIN_ID, "state", None)
        else:
            send_message(chat_id, "❌ عدد بفرست!", get_admin_keyboard())
        return
    
    if admin_state == "admin_broadcast" and is_admin(user_id):
        if text == "🔙 بازگشت":
            save_user_setting(ADMIN_ID, "state", None)
            send_message(chat_id, "🔙 برگشتی.", get_admin_keyboard())
            return
        db = load_db(DB_FILE)
        sent = 0
        for uid in db.keys():
            if not is_banned(int(uid)):
                send_message(int(uid), f"📢 **اطلاعیه:**\n\n{text}")
                sent += 1
            time.sleep(0.05)
        send_message(chat_id, f"✅ به {sent} نفر ارسال شد.", get_admin_keyboard())
        save_user_setting(ADMIN_ID, "state", None)
        return
    
    user = get_user(user_id)
    if not user:
        send_message(chat_id, "❌ /start بزن", main_keyboard())
        return
    
    user_state = get_user_settings(user_id).get("state")
    
    if user_state == "waiting_for_invite_number":
        if text == "🔙 بازگشت":
            save_user_setting(user_id, "state", None)
            send_message(chat_id, profile_text(user), main_keyboard())
            return
        if text.isdigit():
            num = int(text)
            real_invites = get_user_settings(user_id).get("real_invites", [])
            if 1 <= num <= len(real_invites):
                target_user_id = real_invites[num-1]["user_id"]
                if is_protected(target_user_id):
                    send_message(chat_id, f"❌ **ارسال پیام به این کاربر امکان پذیر نیست!**\n🆔 کاربر: `{target_user_id}`\nاین کاربر دارای اشتراک **طلایی** می‌باشد.", main_keyboard())
                    save_user_setting(user_id, "state", None)
                    return
                save_user_setting(user_id, "pending_new_user", target_user_id)
                save_user_setting(user_id, "state", None)
                show_invite_message(user_id)
            else:
                send_message(chat_id, "❌ عدد اشتباه!", main_keyboard())
        else:
            send_message(chat_id, "❌ عدد بفرست!", main_keyboard())
        return
    
    if user_state == "waiting_for_message" or user_state == "editing_message":
        if text == "🔙 بازگشت":
            save_user_setting(user_id, "state", None)
            show_invite_message(user_id)
            return
        save_user_message(user_id, text)
        save_user_setting(user_id, "state", None)
        send_message(chat_id, f"📝 پیام:\n\n{text}\n\nتایید؟", get_confirm_keyboard())
        return
    
    if text == "📊 پروفایل":
        send_message(chat_id, profile_text(user), profile_keyboard(user.get("ref_code", ""), user_id))
    elif text == "🎯 سوژه ها":
        show_invite_list(user_id)
    elif text == "💎 خرید طلایی":
        send_message(chat_id, "💎 انتخاب کن:", get_gold_plans_keyboard())
    elif text == "📞 پشتیبانی":
        send_message(chat_id, "📝 سوالت رو بنویس:", {"keyboard": [[{"text": "🔙 بازگشت"}], [{"text": "🏠 منو اصلی"}]], "resize_keyboard": True})
        save_user_setting(user_id, "state", "waiting_for_ticket")
    elif user_state == "waiting_for_ticket":
        if text == "🔙 بازگشت":
            save_user_setting(user_id, "state", None)
            send_message(chat_id, profile_text(user), main_keyboard())
            return
        tickets = load_db(TICKETS_FILE)
        ticket_id = str(int(time.time()))
        tickets[ticket_id] = {
            "id": ticket_id,
            "user_id": user_id,
            "message": text,
            "status": "pending",
            "time": datetime.now().isoformat()
        }
        save_db(TICKETS_FILE, tickets)
        send_message(chat_id, "✅ تیکت ثبت شد!", main_keyboard())
        send_message(ADMIN_ID, f"📩 تیکت جدید:\n🆔 {user_id}\n📝 {text}")
        save_user_setting(user_id, "state", None)
    else:
        send_message(chat_id, profile_text(user), profile_keyboard(user.get("ref_code", ""), user_id))

@app.route('/', methods=['POST'])
def webhook():
    try:
        data = request.json
        if 'message' in data:
            process_message(data['message'])
        elif 'callback_query' in data:
            process_callback(data['callback_query'])
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"خطا: {e}")
        return jsonify({"status": "error"})

@app.route('/setwebhook', methods=['GET'])
def set_webhook():
    webhook_url = f"https://{BOT_USERNAME}.onrender.com/"
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
    try:
        response = requests.get(url)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/', methods=['GET'])
def index():
    return "ربات روشن است! 🚀"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
