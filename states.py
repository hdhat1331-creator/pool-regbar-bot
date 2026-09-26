# حالت‌های کاربر
WAITING_FOR_INVITE_NUMBER = "waiting_for_invite_number"
WAITING_FOR_MESSAGE = "waiting_for_message"
WAITING_FOR_TICKET = "waiting_for_ticket"

# حالت‌های ادمین
ADMIN_BAN_USER = "admin_ban_user"
ADMIN_GRANT_GOLD = "admin_grant_gold"
ADMIN_BROADCAST = "admin_broadcast"
ADMIN_BLOCK_USER = "admin_block_user"
ADMIN_GOLD_MESSAGE = "admin_gold_message"
ADMIN_TICKET_REPLY = "admin_ticket_reply"

# استور در حافظه
user_states = {}   # user_id -> state
user_data = {}     # user_id -> dict داده‌های موقت
```

---

📁 3️⃣ handlers.py (خیلی بزرگه، تکه‌تکه می‌فرستم)

تکه‌ی ۱:

```python
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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


def is_admin(user_id):
    return user_id == ADMIN_ID


async def safe_send(bot, chat_id, text, **kwargs):
    try:
        await bot.send_message(chat_id, text, **kwargs)
        return True
    except TelegramError:
        return False
