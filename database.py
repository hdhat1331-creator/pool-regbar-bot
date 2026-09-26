import random
import string
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME, INVITE_REWARD, SIGNUP_BONUS

_client = None
_db = None


def get_db():
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(MONGO_URI)
        _db = _client[DB_NAME]
    return _db


def users_col():
    return get_db()["users"]

def invites_col():
    return get_db()["invites"]

def messages_col():
    return get_db()["messages"]

def tickets_col():
    return get_db()["tickets"]

def gold_requests_col():
    return get_db()["gold_requests"]

def blocked_col():
    return get_db()["blocked"]

def banned_col():
    return get_db()["banned"]


def gen_ref_code(length=8):
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def get_user(user_id):
    return await users_col().find_one({"id": str(user_id)})


async def create_user(user_id, ref_by=None):
    uid = str(user_id)
    existing = await get_user(uid)
    if existing:
        return existing

    ref_code = gen_ref_code()
    while await users_col().find_one({"ref_code": ref_code}):
        ref_code = gen_ref_code()

    doc = {
        "id": uid,
        "balance": SIGNUP_BONUS,
        "ref_code": ref_code,
        "ref_by": ref_by,
        "invite_count": 0,
        "subscription_type": "عادی",
        "subscription_expire": None,
        "reg_date": now_str(),
    }
    await users_col().insert_one(doc)

    if ref_by:
        await invites_col().update_one(
            {"id": ref_by},
            {"$push": {"invites": {"user_id": uid, "time": now_str()}}},
            upsert=True,
        )
        await users_col().update_one(
            {"id": ref_by},
            {"$inc": {"balance": INVITE_REWARD, "invite_count": 1}},
        )
    return doc


async def update_user(user_id, data):
    await users_col().update_one({"id": str(user_id)}, {"$set": data})


async def get_all_users():
    cursor = users_col().find({})
    return await cursor.to_list(length=None)


async def get_user_by_ref_code(ref_code):
    return await users_col().find_one({"ref_code": ref_code})


async def get_invites(user_id):
    doc = await invites_col().find_one({"id": str(user_id)})
    if not doc:
        return []
    return doc.get("invites", [])


async def is_gold(user_id):
    user = await get_user(user_id)
    if not user:
        return False
    if user.get("subscription_type") != "طلایی":
        return False
    exp = user.get("subscription_expire")
    if not exp:
        return False
    try:
        exp_dt = datetime.strptime(exp, "%Y-%m-%d %H:%M:%S")
        if exp_dt < datetime.now():
            await update_user(user_id, {"subscription_type": "عادی", "subscription_expire": None})
            return False
        return True
    except Exception:
        return False


async def grant_gold(user_id, days):
    exp = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    await update_user(user_id, {
        "subscription_type": "طلایی",
        "subscription_expire": exp,
    })
    return exp


async def save_message(user_id, message):
    await messages_col().update_one(
        {"id": str(user_id)},
        {"$set": {"message": message, "time": now_str()}},
        upsert=True,
    )


async def get_message(user_id):
    doc = await messages_col().find_one({"id": str(user_id)})
    if not doc:
        return None
    return doc.get("message")


async def add_ticket(user_id, message):
    tid = f"{int(datetime.now().timestamp() * 1000)}_{user_id}"
    await tickets_col().insert_one({
        "id": tid,
        "user_id": str(user_id),
        "message": message,
        "status": "pending",
        "reply": None,
        "time": now_str(),
    })
    return tid


async def get_pending_tickets():
    cursor = tickets_col().find({"status": "pending"})
    return await cursor.to_list(length=None)


async def get_ticket(tid):
    return await tickets_col().find_one({"id": tid})


async def update_ticket(tid, data):
    await tickets_col().update_one({"id": tid}, {"$set": data})


async def add_gold_request(user_id, plan_key, plan):
    existing = await gold_requests_col().find_one({"user_id": str(user_id), "status": "pending"})
    if existing:
        return None
    doc = {
        "id": f"gr_{int(datetime.now().timestamp() * 1000)}",
        "user_id": str(user_id),
        "plan": plan["name"],
        "days": plan["days"],
        "price": plan["price"],
        "status": "pending",
        "time": now_str(),
    }
    await gold_requests_col().insert_one(doc)
    return doc


async def get_gold_request(user_id):
    return await gold_requests_col().find_one({"user_id": str(user_id), "status": "pending"})


async def approve_gold_request(user_id):
    await gold_requests_col().update_one(
        {"user_id": str(user_id), "status": "pending"},
        {"$set": {"status": "approved"}},
    )


async def block_user(user_id):
    await blocked_col().update_one(
        {"id": str(user_id)}, {"$set": {"id": str(user_id)}}, upsert=True
    )


async def unblock_user(user_id):
    await blocked_col().delete_one({"id": str(user_id)})


async def is_blocked(user_id):
    return await blocked_col().find_one({"id": str(user_id)}) is not None


async def get_blocked_count():
    return await blocked_col().count_documents({})


async def ban_user(user_id, ban_type, until=None):
    await banned_col().update_one(
        {"id": str(user_id)},
        {"$set": {"id": str(user_id), "type": ban_type, "until": until}},
        upsert=True,
    )


async def unban_user(user_id):
    await banned_col().delete_one({"id": str(user_id)})


async def get_ban(user_id):
    doc = await banned_col().find_one({"id": str(user_id)})
    if not doc:
        return None
    if doc.get("type") == "temporary" and doc.get("until"):
        try:
            until_dt = datetime.strptime(doc["until"], "%Y-%m-%d %H:%M:%S")
            if until_dt < datetime.now():
                await unban_user(user_id)
                return None
        except Exception:
            pass
    return doc


async def get_banned_count():
    return await banned_col().count_documents({})


async def get_stats():
    total = await users_col().count_documents({})
    gold = await users_col().count_documents({"subscription_type": "طلایی"})
    banned = await get_banned_count()
    blocked = await get_blocked_count()
    return {
        "total": total,
        "gold": gold,
        "regular": total - gold,
        "banned": banned,
        "blocked": blocked,
                     }
