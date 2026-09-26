import asyncio
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from config import (
    ADMIN_ID, GOLD_PLANS, INVITE_REWARD, SIGNUP_BONUS,
    REGULAR_MAX_MESSAGES, REGULAR_MAX_LINES, REGULAR_MAX_INVITES,
    REGULAR_DELAY, GOLD_MAX_MESSAGES, GOLD_DELAY,
)
from database import (
    get_user, create_user, update_user, get_all_users,
    get_user_by_ref_code, get_invites, is_gold, grant_gold,
    save_message, get_message, add_ticket, get_pending_tickets,
    get_ticket, update_ticket, add_gold_request, get_gold_request,
    approve_gold_request, block_user, unblock_user, is_blocked,
    ban_user, unban_user, get_ban, get_stats,
    users_col, invites_col, gen_ref_code,
)
from keyboards import (
    main_menu, admin_menu, back_menu, gold_plans_kb, profile_kb,
    subject_kb, count_kb, confirm_msg_kb, ban_duration_kb,
    grant_gold_kb, ticket_kb, confirm_reply_kb, reset_confirm_kb,
    block_confirm_kb, gold_request_kb, back_to_admin_kb,
)
from states import (
    user_states, user_data,
    WAITING_FOR_INVITE_NUMBER, WAITING_FOR_MESSAGE, WAITING_FOR_TICKET,
    ADMIN_BAN_USER, ADMIN_GRANT_GOLD, ADMIN_BROADCAST, ADMIN_BLOCK_USER,
    ADMIN_GOLD_MESSAGE, ADMIN_TICKET_REPLY,
)


HELP_TEXT = """📖 راهنمای ربات پول رگبار

🔹 هدف ربات:
ارسال پیام رگباری به کاربرانی که از طریق لینک دعوت شما وارد ربات شده اند.

🔹 نحوه کار:
1️⃣ لینک دعوت خود را از بخش پروفایل کپی کنید
2️⃣ برای دوستان خود بفرستید
3️⃣ با ورود هر کاربر، به شما اطلاع داده می شود
4️⃣ می توانید پیام و تعداد ارسال را تنظیم کنید

💰 کسب درآمد صرفا ظاهر ربات است!
هدف اصلی ربات ارسال پیام رگباری می باشد.

📊 مقایسه کاربر عادی و طلایی:

🟢 کاربر عادی:
• حداکثر ۵۰ پیام در هر بار
• حداکثر ۵ خط برای هر پیام
• حداکثر ۱۵ دعوت
• سرعت ارسال: هر ۲ ثانیه یک پیام

🟡 کاربر طلایی:
• بدون محدودیت تعداد پیام
• بدون محدودیت خطوط
• دعوت نامحدود
• سرعت ارسال: هر ثانیه ۳ پیام
• مشاهده سوژه های ویژه
• پشتیبانی اختصاصی

💡 نکته: برای دریافت اشتراک طلایی، از گزینه «💎 خرید طلایی» استفاده کنید."""


def is_admin(user_id):
    return user_id == ADMIN_ID


# ============================================================
# /start
# ============================================================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    args = context.args

    ban = await get_ban(uid)
    if ban:
        await update.message.reply_text("🚫 شما مسدود شده اید!")
        return

    ref_by = None
    if args and args[0]:
        ref_code = args[0]
        ref_user = await get_user_by_ref_code(ref_code)
        if ref_user and str(ref_user["id"]) != str(uid):
            ref_by = str(ref_user["id"])

    is_new = await get_user(uid) is None
    await create_user(uid, ref_by)

    if is_new and ref_by:
        try:
            await context.bot.send_message(
                int(ref_by),
                "🎁 ۵۰,۰۰۰ تومان جایزه دعوت به حساب شما واریز شد!"
            )
            await context.bot.send_message(
                int(ref_by),
                f"🎯 سوژه جدید وارد شد!\n\n🆔 کاربر: `{uid}`\n\nاز دکمه های زیر استفاده کنید:",
                reply_markup=subject_kb(),
                parse_mode="Markdown",
            )
        except TelegramError:
            pass

    if is_admin(uid):
        await update.message.reply_text("👑 پنل ادمین:", reply_markup=admin_menu())
    else:
        await update.message.reply_text("🏠 منوی اصلی:", reply_markup=main_menu())


# ============================================================
# متن‌ها
# ============================================================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    text = update.message.text
    state = user_states.get(uid)
    is_adm = is_admin(uid)

    ban = await get_ban(uid)
    if ban:
        await update.message.reply_text("🚫 شما مسدود شده اید!")
        return

    # ---- حالت‌های انتظار ----
    if state == WAITING_FOR_INVITE_NUMBER:
        await handle_invite_number(update, context, text); return
    if state == WAITING_FOR_MESSAGE:
        await handle_message_set(update, context, text); return
    if state == WAITING_FOR_TICKET:
        await handle_ticket(update, context, text); return
    if state == ADMIN_BAN_USER:
        await handle_admin_ban_id(update, context, text); return
    if state == ADMIN_GRANT_GOLD:
        await handle_admin_grant_id(update, context, text); return
    if state == ADMIN_BROADCAST:
        await handle_broadcast(update, context, text); return
    if state == ADMIN_BLOCK_USER:
        await handle_admin_block_id(update, context, text); return
    if state == ADMIN_GOLD_MESSAGE:
        await handle_admin_gold_msg(update, context, text); return
    if state == ADMIN_TICKET_REPLY:
        await handle_admin_ticket_reply(update, context, text); return

    # ---- دکمه‌های کاربر ----
    if text == "🎯 سوژه ها":
        await show_subjects(update, context); return
    if text == "💎 خرید طلایی":
        await update.message.reply_text("پلن مورد نظر رو انتخاب کن:", reply_markup=gold_plans_kb()); return
    if text == "📖 راهنما":
        await update.message.reply_text(HELP_TEXT, parse_mode="Markdown"); return
    if text == "📊 پروفایل":
        await show_profile(update, context); return
    if text == "📞 پشتیبانی":
        user_states[uid] = WAITING_FOR_TICKET
        await update.message.reply_text("📝 مشکل یا سوال خود را بنویسید:", reply_markup=back_menu()); return
    if text == "🔙 بازگشت" or text == "🏠 منو اصلی":
        user_states.pop(uid, None)
        user_data.pop(uid, None)
        if is_adm:
            await update.message.reply_text("👑 پنل ادمین:", reply_markup=admin_menu())
        else:
            await update.message.reply_text("🏠 منوی اصلی:", reply_markup=main_menu())
        return

    # ---- دکمه‌های ادمین ----
    if is_adm:
        if text == "📊 آمار کاربران":
            stats = await get_stats()
            await update.message.reply_text(
                f"📊 آمار کاربران:\n\n"
                f"👥 کل کاربران: {stats['total']}\n"
                f"🟢 کاربران عادی: {stats['regular']}\n"
                f"🟡 کاربران طلایی: {stats['gold']}\n"
                f"🚫 مسدود شده ها: {stats['banned']}\n"
                f"🔒 مسدود از دریافت پیام: {stats['blocked']}"
            )
            return
        if text == "🚫 مسدود کردن کاربر":
            user_states[uid] = ADMIN_BAN_USER
            await update.message.reply_text("🆔 آیدی عددی کاربر را ارسال کنید:", reply_markup=back_menu()); return
        if text == "🎁 اعطای اشتراک طلایی":
            user_states[uid] = ADMIN_GRANT_GOLD
            await update.message.reply_text("🆔 آیدی عددی کاربر را ارسال کنید:", reply_markup=back_menu()); return
        if text == "📩 تیکت ها":
            await show_tickets(update, context); return
        if text == "📢 اطلاع رسانی":
            user_states[uid] = ADMIN_BROADCAST
            await update.message.reply_text("📝 پیام اطلاع رسانی خود را بنویسید:", reply_markup=back_menu()); return
        if text == "🔄 ریست کاربران عادی":
            await update.message.reply_text("⚠️ مطمئنی؟ همه کاربران عادی ریست میشن.", reply_markup=reset_confirm_kb()); return
        if text == "🔒 مسدود کردن دریافت پیام":
            user_states[uid] = ADMIN_BLOCK_USER
            await update.message.reply_text("🆔 آیدی کاربر را ارسال کنید:", reply_markup=back_menu()); return
        if text == "⚙️ تنظیمات":
            await update.message.reply_text(
                "⚙️ تنظیمات ربات:\n\n"
                "💰 مبلغ جایزه دعوت: ۵۰,۰۰۰ تومان\n"
                "💎 قیمت اشتراک طلایی:\n"
                "   • ۷ روزه: ۵۰,۰۰۰ تومان\n"
                "   • ۱۴ روزه: ۱۰۰,۰۰۰ تومان\n"
                "   • یکماهه: ۱۲۰,۰۰۰ تومان\n"
                "📨 محدودیت پیام عادی: ۵۰ پیام\n"
                "📝 محدودیت خطوط: ۵ خط\n"
                "👥 محدودیت دعوت: ۱۵ نفر"
            )
            return
        if text == "👤 حالت کاربر عادی":
            user_data[uid] = user_data.get(uid, {})
            user_data[uid]["as_regular"] = True
            await update.message.reply_text("👤 حالت کاربر عادی فعال شد.", reply_markup=main_menu()); return
        if text == "👑 بازگشت به پنل ادمین":
            user_data.pop(uid, None)
            await update.message.reply_text("👑 پنل ادمین:", reply_markup=admin_menu()); return


# ============================================================
# سوژه‌ها
# ============================================================
async def show_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    invites = await get_invites(uid)
    if not invites:
        await update.message.reply_text("❌ شما هنوز کسی را دعوت نکرده اید!")
        return
    lines = ["📋 لیست دعوت شده ها:\n"]
    for i, inv in enumerate(invites, 1):
        lines.append(f"{i}. 🆔 {inv['user_id']} - 🕐 {inv['time']}")
    lines.append("\n🔢 عدد مورد نظر را ارسال کنید:")
    user_states[uid] = WAITING_FOR_INVITE_NUMBER
    user_data[uid] = {"invites": invites}
    await update.message.reply_text("\n".join(lines), reply_markup=back_menu())


async def handle_invite_number(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    uid = update.effective_user.id
    if not text.isdigit():
        await update.message.reply_text("❌ لطفا یک عدد ارسال کنید.")
        return
    num = int(text)
    invites = user_data.get(uid, {}).get("invites", [])
    if num < 1 or num > len(invites):
        await update.message.reply_text("❌ عدد نامعتبر.")
        return
    target_id = invites[num - 1]["user_id"]
    if await is_blocked(target_id):
        await update.message.reply_text("❌ این کاربر مسدود از دریافت پیام است.")
        return
    user_data[uid]["target"] = target_id
    user_states.pop(uid, None)
    await update.message.reply_text(
        f"🎯 سوژه انتخاب شد:\n🆔 {target_id}\n\nاز دکمه های زیر استفاده کنید:",
        reply_markup=subject_kb()
    )


async def handle_message_set(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    uid = update.effective_user.id
    gold = await is_gold(uid)
    lines = text.split("\n")
    if not gold and len(lines) > REGULAR_MAX_LINES:
        await update.message.reply_text(f"❌ حداکثر {REGULAR_MAX_LINES} خط برای کاربر عادی.")
        return
    target = user_data.get(uid, {}).get("target")
    if not target:
        await update.message.reply_text("❌ اول یه سوژه انتخاب کن.")
        user_states.pop(uid, None)
        return
    await save_message(uid, text)
    user_states.pop(uid, None)
    await update.message.reply_text(
        f"📝 پیام ذخیره شد:\n{text}\n\nتایید؟",
        reply_markup=confirm_msg_kb()
    )


async def handle_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    uid = update.effective_user.id
    tid = await add_ticket(uid, text)
    user_states.pop(uid, None)
    await update.message.reply_text("✅ تیکت شما ثبت شد.", reply_markup=main_menu())
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"📩 تیکت جدید:\n\n🆔 کاربر: `{uid}`\n📝 {text}\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            parse_mode="Markdown",
            reply_markup=ticket_kb(tid)
        )
    except TelegramError:
        pass


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = await get_user(uid)
    if not user:
        await update.message.reply_text("❌ اول /start بزن.")
        return
    text = (
        f"👤 پروفایل کاربری\n\n"
        f"🆔 شناسه: `{uid}`\n"
        f"💰 موجودی: {user.get('balance', 0):,} تومان\n"
        f"👥 دعوت شده ها: {user.get('invite_count', 0)} نفر\n"
        f"📊 نوع اشتراک: {user.get('subscription_type', 'عادی')}\n\n"
        f"🔗 لینک دعوت:\n"
        f"`https://t.me/POOLREGBARR_BOT?start={user.get('ref_code', '')}`"
    )
    if user.get("subscription_type") == "طلایی" and user.get("subscription_expire"):
        text += f"\n\n⏳ انقضا: {user['subscription_expire']}"
    await update.message.reply_text(text, reply_markup=profile_kb(), parse_mode="Markdown")


# ============================================================
# ادمین: بن، گلد، برودکست، بلوک، تیکت
# ============================================================
async def handle_admin_ban_id(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    uid = update.effective_user.id
    if not text.isdigit():
        await update.message.reply_text("❌ آیدی عددی نامعتبر.")
        return
    target = text.strip()
    user_states.pop(uid, None)
    await update.message.reply_text(
        f"مدت بن برای `{target}`:",
        reply_markup=ban_duration_kb(target),
        parse_mode="Markdown"
    )


async def handle_admin_grant_id(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    uid = update.effective_user.id
    if not text.isdigit():
        await update.message.reply_text("❌ آیدی عددی نامعتبر.")
        return
    target = text.strip()
    user_states.pop(uid, None)
    await update.message.reply_text(
        f"مدت اشتراک طلایی برای `{target}`:",
        reply_markup=grant_gold_kb(target),
        parse_mode="Markdown"
    )


async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    uid = update.effective_user.id
    user_states.pop(uid, None)
    await update.message.reply_text("📢 دارم می فرستم...")
    users = await get_all_users()
    sent = 0
    for u in users:
        ban = await get_ban(u["id"])
        if ban:
            continue
        try:
            await context.bot.send_message(int(u["id"]), text)
            sent += 1
            await asyncio.sleep(0.05)
        except TelegramError:
            continue
    await update.message.reply_text(f"✅ ارسال شد به {sent} کاربر.", reply_markup=admin_menu())


async def handle_admin_block_id(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    uid = update.effective_user.id
    if not text.isdigit():
        await update.message.reply_text("❌ آیدی عددی نامعتبر.")
        return
    target = text.strip()
    user_states.pop(uid, None)
    blocked = await is_blocked(target)
    msg = "🔒 کاربر در حال حاضر مسدود از دریافت پیام است. رفع مسدودیت؟" if blocked else "🔓 کاربر مسدود نیست. مسدود کنم؟"
    await update.message.reply_text(msg, reply_markup=block_confirm_kb(target, blocked))


async def handle_admin_gold_msg(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    uid = update.effective_user.id
    info = user_data.get(uid, {})
    target = info.get("gold_target")
    if not target:
        user_states.pop(uid, None)
        await update.message.reply_text("❌ خطا.", reply_markup=admin_menu())
        return
    try:
        await context.bot.send_message(int(target), text)
        await update.message.reply_text("✅ پیام ارسال شد.", reply_markup=admin_menu())
    except TelegramError:
        await update.message.reply_text("❌ ارسال نشد.", reply_markup=admin_menu())
    user_states.pop(uid, None)
    user_data.pop(uid, None)


async def handle_admin_ticket_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    uid = update.effective_user.id
    tid = user_data.get(uid, {}).get("ticket_id")
    if not tid:
        user_states.pop(uid, None)
        await update.message.reply_text("❌ خطا.", reply_markup=admin_menu())
        return
    user_data[uid]["reply_text"] = text
    await update.message.reply_text(
        f"📝 پاسخ شما:\n{text}\n\nارسال شود؟",
        reply_markup=confirm_reply_kb(tid)
    )


async def show_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tickets = await get_pending_tickets()
    if not tickets:
        await update.message.reply_text("✅ هیچ تیکت پاسخ داده نشده ای وجود ندارد.")
        return
    for t in tickets[:10]:
        await update.message.reply_text(
            f"📩 تیکت جدید:\n\n🆔 کاربر: `{t['user_id']}`\n📝 {t['message']}\n🕐 {t['time']}",
            parse_mode="Markdown",
            reply_markup=ticket_kb(t["id"])
        )


# ============================================================
# ارسال رگباری
# ============================================================
async def send_subject_messages(bot, sender_id, message, count):
    invites = await get_invites(sender_id)
    if not invites:
        return 0, 0
    gold = await is_gold(sender_id)
    delay = GOLD_DELAY if gold else REGULAR_DELAY
    max_count = GOLD_MAX_MESSAGES if gold else REGULAR_MAX_MESSAGES
    count = min(count, max_count, len(invites))
    sent = 0
    fail = 0
    for inv in invites[:count]:
        target = inv["user_id"]
        if await is_blocked(target):
            fail += 1
            continue
        try:
            await bot.send_message(int(target), message)
            sent += 1
        except TelegramError:
            fail += 1
        await asyncio.sleep(delay)
    return sent, fail


async def run_broadcast_task(bot, sender_id, message, count, chat_id):
    sent, fail = await send_subject_messages(bot, sender_id, message, count)
    try:
        await bot.send_message(
            chat_id,
            f"✅ ارسال شد!\n\n✔️ موفق: {sent}\n❌ ناموفق: {fail}",
            reply_markup=main_menu()
        )
    except TelegramError:
        pass


# ============================================================
# Callback Query
# ============================================================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data
    is_adm = is_admin(uid)

    if data == "back_main":
        if is_adm:
            await q.edit_message_text("👑 پنل ادمین:")
        else:
            await q.edit_message_text("🏠 منو اصلی:")
        return

    if data == "admin_back":
        await q.edit_message_text("👑 پنل ادمین:")
        return

    # خرید طلایی
    if data.startswith("gold_buy_"):
        plan_key = data.replace("gold_buy_", "")
        plan = GOLD_PLANS.get(plan_key)
        if not plan:
            return
        existing = await get_gold_request(uid)
        if existing:
            await q.edit_message_text("❌ شما قبلا درخواست ثبت کرده اید!")
            return
        await add_gold_request(uid, plan_key, plan)
        await q.edit_message_text("✅ درخواست شما ثبت شد!")
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"📩 درخواست اشتراک طلایی جدید!\n\n"
                f"🆔 کاربر: `{uid}`\n"
                f"📦 پلن: {plan['name']}\n"
                f"💰 قیمت: {plan['price']:,} تومان",
                parse_mode="Markdown",
                reply_markup=gold_request_kb(uid)
            )
        except TelegramError:
            pass
        return

    # پروفایل
    if data == "copy_invite":
        user = await get_user(uid)
        if user:
            await q.message.reply_text(f"https://t.me/POOLREGBARR_BOT?start={user['ref_code']}")
        return
    if data == "copy_id":
        await q.message.reply_text(str(uid))
        return

    # سوژه
    if data == "subj_set_msg":
        user_states[uid] = WAITING_FOR_MESSAGE
        await q.edit_message_text("✏️ پیام خود را بنویسید:")
        return
    if data == "subj_count":
        await q.edit_message_text("🔢 تعداد پیام:", reply_markup=count_kb())
        return
    if data.startswith("cnt_"):
        count = int(data.replace("cnt_", ""))
        user_data[uid] = user_data.get(uid, {})
        user_data[uid]["count"] = count
        gold = await is_gold(uid)
        max_c = GOLD_MAX_MESSAGES if gold else REGULAR_MAX_MESSAGES
        if count > max_c:
            await q.edit_message_text(f"❌ حداکثر {max_c} پیام برای شما.")
            return
        await q.edit_message_text(f"✅ تعداد {count} ثبت شد.", reply_markup=subject_kb())
        return
    if data == "subj_send":
        target = user_data.get(uid, {}).get("target")
        msg = await get_message(uid)
        count = user_data.get(uid, {}).get("count")
        if not target:
            await q.edit_message_text("❌ اول یه سوژه انتخاب کن."); return
        if not msg:
            await q.edit_message_text("❌ اول پیام رو تنظیم کن."); return
        if not count:
            await q.edit_message_text("❌ اول تعداد رو انتخاب کن."); return
        await q.edit_message_text(f"⏳ در حال ارسال {count} پیام...")
        asyncio.create_task(run_broadcast_task(context.bot, uid, msg, count, q.message.chat_id))
        return
    if data == "subj_msg_ok":
        await q.edit_message_text("✅ پیام تایید شد. حالا تعداد رو انتخاب کن:", reply_markup=count_kb())
        return
    if data == "subj_back":
        await q.edit_message_text("🎯 از دکمه های زیر استفاده کنید:", reply_markup=subject_kb())
        return

    # بن
    if data.startswith("ban_"):
        parts = data.split("_")
        if parts[1] == "perm":
            target = parts[2]
            await ban_user(target, "permanent")
        else:
            days = int(parts[1])
            target = parts[2]
            until = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            await ban_user(target, "temporary", until)
        await q.edit_message_text(f"✅ کاربر `{target}` بن شد.", parse_mode="Markdown")
        return

    # گلد
    if data.startswith("gg_"):
        parts = data.split("_")
        days = int(parts[1])
        target = parts[2]
        exp = await grant_gold(target, days)
        await q.edit_message_text(f"✅ اشتراک {days} روزه برای `{target}` فعال شد.", parse_mode="Markdown")
        try:
            await context.bot.send_message(
                int(target),
                f"🎉 تبریک! اشتراک طلایی شما فعال شد!\n\n📦 مدت: {days} روز\n📅 تا: {exp}\n\n"
                f"✨ مزایا:\n• ارسال بدون محدودیت\n• دعوت نامحدود\n• سرعت بالا\n• پشتیبانی اختصاصی"
            )
        except TelegramError:
            pass
        return

    # ریست
    if data == "reset_yes":
        users = await get_all_users()
        count = 0
        for u in users:
            if u.get("subscription_type") == "طلایی":
                continue
            await update_user(u["id"], {
                "balance": SIGNUP_BONUS,
                "invite_count": 0,
                "ref_code": gen_ref_code(),
            })
            await invites_col().delete_one({"id": u["id"]})
            count += 1
        await q.edit_message_text(f"✅ {count} کاربر عادی ریست شد.")
        return
    if data == "reset_no":
        await q.edit_message_text("لغو شد.")
        return

    # بلوک
    if data.startswith("blk_add_"):
        target = data.replace("blk_add_", "")
        await block_user(target)
        await q.edit_message_text(f"🔒 کاربر `{target}` مسدود شد.", parse_mode="Markdown")
        return
    if data.startswith("blk_rem_"):
        target = data.replace("blk_rem_", "")
        await unblock_user(target)
        await q.edit_message_text(f"🔓 کاربر `{target}` آزاد شد.", parse_mode="Markdown")
        return

    # تیکت
    if data.startswith("tk_reply_"):
        tid = data.replace("tk_reply_", "")
        user_states[uid] = ADMIN_TICKET_REPLY
        user_data[uid] = {"ticket_id": tid}
        await q.edit_message_text("📝 پاسخ خود را بنویسید:")
        return
    if data.startswith("tk_done_"):
        tid = data.replace("tk_done_", "")
        await update_ticket(tid, {"status": "answered"})
        await q.edit_message_text("✅ تیکت بسته شد.")
        return
    if data.startswith("tk_send_"):
        tid = data.replace("tk_send_", "")
        reply_text = user_data.get(uid, {}).get("reply_text", "")
        ticket = await get_ticket(tid)
        if ticket and reply_text:
            try:
                await context.bot.send_message(
                    int(ticket["user_id"]),
                    f"📩 پاسخ تیکت شما:\n\n{reply_text}"
                )
            except TelegramError:
                pass
            await update_ticket(tid, {"status": "answered", "reply": reply_text})
        user_states.pop(uid, None)
        user_data.pop(uid, None)
        await q.edit_message_text("✅ پاسخ ارسال شد.")
        return

    # گلد ریپلای
    if data.startswith("gr_msg_"):
        target = data.replace("gr_msg_", "")
        user_states[uid] = ADMIN_GOLD_MESSAGE
        user_data[uid] = {"gold_target": target}
        await q.edit_message_text("💬 پیام خود را برای کاربر بنویسید:")
        return
    if data.startswith("gr_ok_"):
        target = data.replace("gr_ok_", "")
        req = await get_gold_request(target)
        if req:
            exp = await grant_gold(target, req["days"])
            await approve_gold_request(target)
            await q.edit_message_text(f"✅ اشتراک {req['days']} روزه فعال شد.")
            try:
                await context.bot.send_message(
                    int(target),
                    f"🎉 تبریک! اشتراک طلایی شما فعال شد!\n\n📦 مدت: {req['days']} روز\n📅 تا: {exp}"
                )
            except TelegramError:
                pass
        return
