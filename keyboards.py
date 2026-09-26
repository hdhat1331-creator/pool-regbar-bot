from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup


# ============ منوی اصلی کاربر ============
def main_menu():
    kb = [
        ["🎯 سوژه ها", "💎 خرید طلایی"],
        ["📖 راهنما", "📊 پروفایل"],
        ["📞 پشتیبانی"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


# ============ منوی ادمین ============
def admin_menu():
    kb = [
        ["📊 آمار کاربران", "🚫 مسدود کردن کاربر"],
        ["🎁 اعطای اشتراک طلایی", "📩 تیکت ها"],
        ["📢 اطلاع رسانی", "🔄 ریست کاربران عادی"],
        ["🔒 مسدود کردن دریافت پیام", "⚙️ تنظیمات"],
        ["👤 حالت کاربر عادی"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


# ============ کیبورد بازگشت ============
def back_menu():
    kb = [["🔙 بازگشت", "🏠 منو اصلی"]]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


# ============ پلن‌های طلایی ============
def gold_plans_kb():
    kb = [
        [InlineKeyboardButton("💎 ۷ روزه - ۵۰,۰۰۰ تومان", callback_data="gold_buy_gold_7")],
        [InlineKeyboardButton("💎 ۱۴ روزه - ۱۰۰,۰۰۰ تومان", callback_data="gold_buy_gold_14")],
        [InlineKeyboardButton("💎 یکماهه - ۱۲۰,۰۰۰ تومان", callback_data="gold_buy_gold_30")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(kb)


# ============ پروفایل ============
def profile_kb():
    kb = [
        [InlineKeyboardButton("📋 کپی لینک دعوت", callback_data="copy_invite")],
        [InlineKeyboardButton("🆔 کپی آیدی عددی", callback_data="copy_id")],
    ]
    return InlineKeyboardMarkup(kb)


# ============ تنظیم پیام (سوژه) ============
def subject_kb():
    kb = [
        [InlineKeyboardButton("✏️ تنظیم پیام", callback_data="subj_set_msg"),
         InlineKeyboardButton("🔢 تعداد پیام", callback_data="subj_count")],
        [InlineKeyboardButton("✅ تایید و ارسال", callback_data="subj_send")],
    ]
    return InlineKeyboardMarkup(kb)


# ============ تعداد پیام ============
def count_kb():
    kb = [
        [InlineKeyboardButton("۱۰ پیام", callback_data="cnt_10"),
         InlineKeyboardButton("۵۰ پیام", callback_data="cnt_50")],
        [InlineKeyboardButton("۱۰۰ پیام", callback_data="cnt_100"),
         InlineKeyboardButton("۲۰۰ پیام", callback_data="cnt_200")],
        [InlineKeyboardButton("۴۰۰ پیام", callback_data="cnt_400"),
         InlineKeyboardButton("۸۰۰ پیام", callback_data="cnt_800")],
        [InlineKeyboardButton("۱۶۰۰ پیام", callback_data="cnt_1600"),
         InlineKeyboardButton("۳۲۰۰ پیام", callback_data="cnt_3200")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="subj_back")],
    ]
    return InlineKeyboardMarkup(kb)


# ============ تایید پیام ============
def confirm_msg_kb():
    kb = [
        [InlineKeyboardButton("✏️ تنظیم دوباره", callback_data="subj_set_msg"),
         InlineKeyboardButton("✅ بله", callback_data="subj_msg_ok")],
    ]
    return InlineKeyboardMarkup(kb)


# ============ بن (مدت) ============
def ban_duration_kb(user_id):
    kb = [
        [InlineKeyboardButton("۱ روز", callback_data=f"ban_1_{user_id}"),
         InlineKeyboardButton("۳ روز", callback_data=f"ban_3_{user_id}")],
        [InlineKeyboardButton("۷ روز", callback_data=f"ban_7_{user_id}"),
         InlineKeyboardButton("۱۴ روز", callback_data=f"ban_14_{user_id}")],
        [InlineKeyboardButton("۳۰ روز", callback_data=f"ban_30_{user_id}")],
        [InlineKeyboardButton("🔒 دائمی", callback_data=f"ban_perm_{user_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(kb)


# ============ اشتراک طلایی (ادمین) ============
def grant_gold_kb(user_id):
    kb = [
        [InlineKeyboardButton("🎁 ۷ روزه", callback_data=f"gg_7_{user_id}")],
        [InlineKeyboardButton("🎁 ۱۴ روزه", callback_data=f"gg_14_{user_id}")],
        [InlineKeyboardButton("🎁 یکماهه", callback_data=f"gg_30_{user_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(kb)


# ============ تیکت (ادمین) ============
def ticket_kb(tid):
    kb = [
        [InlineKeyboardButton("📝 پاسخ", callback_data=f"tk_reply_{tid}")],
        [InlineKeyboardButton("✅ پاسخ داده شد", callback_data=f"tk_done_{tid}")],
    ]
    return InlineKeyboardMarkup(kb)


# ============ تایید تیکت پاسخ ============
def confirm_reply_kb(tid):
    kb = [
        [InlineKeyboardButton("✅ ارسال", callback_data=f"tk_send_{tid}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(kb)


# ============ ریست کاربران ============
def reset_confirm_kb():
    kb = [
        [InlineKeyboardButton("✅ تایید", callback_data="reset_yes"),
         InlineKeyboardButton("❌ لغو", callback_data="reset_no")],
    ]
    return InlineKeyboardMarkup(kb)


# ============ مسدود/آزاد کاربر ============
def block_confirm_kb(user_id, is_blocked):
    if is_blocked:
        kb = [[InlineKeyboardButton("✅ رفع مسدودیت", callback_data=f"blk_rem_{user_id}")],
              [InlineKeyboardButton("❌ لغو", callback_data="admin_back")]]
    else:
        kb = [[InlineKeyboardButton("✅ مسدود کن", callback_data=f"blk_add_{user_id}")],
              [InlineKeyboardButton("❌ لغو", callback_data="admin_back")]]
    return InlineKeyboardMarkup(kb)


# ============ درخواست طلایی (ادمین) ============
def gold_request_kb(user_id):
    kb = [
        [InlineKeyboardButton("💬 ارسال پیام به کاربر", callback_data=f"gr_msg_{user_id}")],
        [InlineKeyboardButton("✅ فعال سازی اشتراک", callback_data=f"gr_ok_{user_id}")],
    ]
    return InlineKeyboardMarkup(kb)


# ============ بازگشت به پنل ادمین ============
def back_to_admin_kb():
    kb = [["👑 بازگشت به پنل ادمین"]]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)
