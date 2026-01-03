import asyncio, json, os, uuid, logging, aiohttp
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, Message, CallbackQuery
from aiohttp import web

# --- 🛠 SETUP LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ⚙️ CONFIG ---
API_TOKEN = '8480954197:AAHAJucatlPOrBl4SsO-369DStOYTJRxCbA'
PORT = int(os.environ.get("PORT", 8080))
DB_FILE = "premium_users.json"
MAX_THREADS = 5 

# --- 🚀 INIT ---
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def get_fancy(text):
    normal = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    fancy  = "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘqʀꜱᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘqʀꜱᴛᴜᴠᴡxʏᴢ₀₁₂₃₄₅₆₇₈₉"
    return text.translate(str.maketrans(normal, fancy))

def progress_bar(current, total, length=10):
    percent = min(1.0, float(current) / total)
    bar = '█' * int(round(percent * length))
    spaces = '░' * (length - len(bar))
    return f"[{bar}{spaces}] {int(percent * 100)}%"

class Setup(StatesGroup):
    waiting_for_url = State()
    waiting_for_amt = State()

# --- 📊 DB PROTECTION ---
def load_db():
    default_db = {"users": {}, "global_stats": {"total_views": 0, "total_likes": 0, "packets_sent": 0}}
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: 
                data = json.load(f)
                if "global_stats" not in data: data["global_stats"] = default_db["global_stats"]
                # Ensure packet counter exists
                if "packets_sent" not in data["global_stats"]: data["global_stats"]["packets_sent"] = 0
                return data
        except Exception as e:
            logger.error(f"DB Load Error: {e}")
    return default_db

db = load_db()
def save_db():
    try:
        with open(DB_FILE, "w") as f: json.dump(db, f, indent=4)
    except Exception as e:
        logger.error(f"DB Save Error: {e}")

# --- ⚡ ENGINE ---
class ZefameEngine:
    def __init__(self, url, s_type):
        self.url = url
        self.service_id = 237 if s_type == 'views' else 234 
        self.endpoint = "https://zefame-free.com/api_free.php?action=order" 
    
    async def request_boost(self, session, sem):
        async with sem:
            try:
                # PostID extraction
                parts = self.url.strip("/").split("/")
                pid = parts[4] if len(parts) > 4 else ""
                data = {"service": self.service_id, "link": self.url, "uuid": str(uuid.uuid4()), "postId": pid}
                headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
                
                async with session.post(self.endpoint, data=data, headers=headers, timeout=12) as r:
                    if r.status == 200:
                        res = await r.json()
                        if res.get('success'): return "OK", None
                        if 'data' in res and isinstance(res['data'], dict):
                            return "WAIT", res['data'].get('timeLeft', 30)
                return "FAIL", None
            except Exception as e:
                return "ERR", str(e)

# --- 🕹️ UI ---
def main_menu(uid):
    u = db["users"].get(str(uid), {"type": "views", "amt": 10, "sent": 0, "packets": 0})
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=f"🚀 {get_fancy('launch turbo')}", callback_data="run"))
    kb.row(InlineKeyboardButton(text=f"🔗 {get_fancy('url')}", callback_data="set_url"), 
           InlineKeyboardButton(text=f"🔢 {get_fancy('batches')}", callback_data="set_amt"))
    mode_label = "👁️ ᴠɪᴇᴡꜱ" if u.get('type') == 'views' else "❤️ ʟɪᴋᴇꜱ"
    kb.row(InlineKeyboardButton(text=f"⚙️ {get_fancy('mode')}: {mode_label}", callback_data="toggle"))
    kb.row(InlineKeyboardButton(text=f"👤 {get_fancy('stats')}", callback_data="me"))
    return kb.as_markup()

@dp.message(Command("start"))
async def cmd_start(m: Message):
    uid = str(m.from_user.id)
    if uid not in db["users"]:
        db["users"][uid] = {"url": "None", "type": "views", "amt": 10, "sent": 0, "packets": 0}
        save_db()
    await m.answer(f"💎 **{get_fancy('god level booster')}**\nStatus: `Turbo Ready` 🚀", reply_markup=main_menu(uid), parse_mode="Markdown")

@dp.callback_query(F.data == "run")
async def start_task(c: CallbackQuery):
    uid = str(c.from_user.id)
    u = db["users"].get(uid)
    if not u or u["url"] == "None": return await c.answer("❌ URL set karo pehle!", show_alert=True)
    
    msg = await c.message.answer(f"🚀 **{get_fancy('initializing turbo engine')}...**")
    engine = ZefameEngine(u["url"], u["type"])
    sem = asyncio.Semaphore(MAX_THREADS)
    done, total = 0, u["amt"]
    
    async with aiohttp.ClientSession() as session:
        while done < total:
            try:
                batch_size = min(total - done, MAX_THREADS)
                tasks = [engine.request_boost(session, sem) for _ in range(batch_size)]
                results = await asyncio.gather(*tasks)
                
                wait_needed = 0
                for status, data in results:
                    if status == "OK":
                        done += 1
                        # Increment counters
                        u["packets"] = u.get("packets", 0) + 1
                        db["global_stats"]["packets_sent"] += 1
                        u["sent"] += (500 if u["type"] == "views" else 20)
                    elif status == "WAIT":
                        wait_needed = max(wait_needed, int(data))
                
                save_db()
                
                # UI With Packet Counter
                await msg.edit_text(
                    f"🔥 **{get_fancy('turbo boosting active')}**\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📈 Progress: `{progress_bar(done, total)}`\n"
                    f"✅ Batches: `{done}/{total}`\n"
                    f"📦 Packets Sent: `{u['packets']}`\n"
                    f"✨ Total Gain: `{u['sent']}` {u['type']}",
                    parse_mode="Markdown"
                )
                
                if wait_needed > 0:
                    for i in range(wait_needed, 0, -5):
                        try: await msg.edit_text(f"⏳ **{get_fancy('api cooldown')}**\nResuming in `{i}s`...")
                        except: pass
                        await asyncio.sleep(5)
                else:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Loop Error: {e}")
                await asyncio.sleep(5)

    await msg.edit_text(f"🏆 **{get_fancy('turbo mission complete')}**\n\n📦 Total Packets: `{u['packets']}`\n✅ Status: Finished")

@dp.callback_query(F.data == "set_url")
async def ask_url(c: CallbackQuery, state: FSMContext):
    await state.set_state(Setup.waiting_for_url)
    await c.message.answer(f"🔗 {get_fancy('send instagram link')}:")

@dp.message(Setup.waiting_for_url)
async def save_url(m: Message, state: FSMContext):
    if "instagram.com" in m.text:
        db["users"][str(m.from_user.id)]["url"] = m.text
        save_db()
        await m.answer("✅ URL Updated!", reply_markup=main_menu(m.from_user.id))
        await state.clear()

@dp.callback_query(F.data == "set_amt")
async def ask_amt(c: CallbackQuery, state: FSMContext):
    await state.set_state(Setup.waiting_for_amt)
    await c.message.answer("🔢 How many batches?")

@dp.message(Setup.waiting_for_amt)
async def save_amt(m: Message, state: FSMContext):
    if m.text.isdigit():
        db["users"][str(m.from_user.id)]["amt"] = int(m.text)
        save_db()
        await m.answer("✅ Amount Updated!", reply_markup=main_menu(m.from_user.id))
        await state.clear()

@dp.callback_query(F.data == "toggle")
async def toggle(c: CallbackQuery):
    uid = str(c.from_user.id)
    db["users"][uid]["type"] = "likes" if db["users"][uid]["type"] == "views" else "views"
    save_db()
    await c.message.edit_reply_markup(reply_markup=main_menu(uid))

# --- 🌐 SERVER ---
async def handle_health(request): return web.Response(text="Turbo Bot Alive")
async def start_web():
    app = web.Application()
    app.router.add_get('/', handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()

async def main():
    asyncio.create_task(start_web())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
