import asyncio, json, os, uuid, logging, aiohttp
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, Message, CallbackQuery
from aiohttp import web

# --- 🛠 CONFIGURATION ---
API_TOKEN = '7983535493:AAHfBSZvH-usRave1ztDLap5EJ2nXx8RwUk'
ADMIN_ID = 8128852482
PORT = int(os.environ.get("PORT", 8080))
DB_FILE = "premium_users.json"
MAX_CONCURRENT_TASKS = 5  # Ek saath kitni requests bhejni hain (Speed Control)

# --- 🧠 FANCY FONT HELPER ---
def get_fancy(text):
    normal = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    fancy  = "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘqʀꜱᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘqʀꜱᴛᴜᴠᴡxʏᴢ₀₁₂₃₄₅₆₇₈₉"
    return text.translate(str.maketrans(normal, fancy))

def progress_bar(current, total, length=10):
    percent = min(1.0, float(current) / total)
    arrow = '█' * int(round(percent * length))
    spaces = '░' * (length - len(arrow))
    return f"[{arrow}{spaces}] {int(percent * 100)}%"

class Setup(StatesGroup):
    waiting_for_url = State()
    waiting_for_amt = State()

# --- 📊 DATABASE ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: pass
    return {"users": {}, "global_stats": {"total_views": 0, "total_likes": 0}}

db = load_db()
def save_db():
    with open(DB_FILE, "w") as f: json.dump(db, f, indent=4)

# --- ⚡ TURBO ENGINE ---
class TurboEngine:
    def __init__(self, url, s_type):
        self.url = url
        self.service_id = 237 if s_type == 'views' else 234 
        self.endpoint = "https://zefame-free.com/api_free.php?action=order" 
        self.headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded",
            "referrer": "https://zefame.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    async def fire_request(self, session, sem):
        async with sem: # Multi-threading limit control
            try:
                pid = ""
                if "/reel/" in self.url: pid = self.url.split("/reel/")[1].split("/")[0]
                elif "/p/" in self.url: pid = self.url.split("/p/")[1].split("/")[0]
                
                data = {"service": self.service_id, "link": self.url, "uuid": str(uuid.uuid4()), "postId": pid}
                async with session.post(self.endpoint, data=data, headers=self.headers, timeout=15) as r:
                    if r.status == 200:
                        res = await r.json()
                        if res.get('success'): return "OK", None
                        if 'data' in res and isinstance(res['data'], dict):
                            return "WAIT", res['data'].get('timeLeft', 30)
                return "FAIL", None
            except:
                return "ERR", None

# --- 🤖 HANDLERS ---
@dp.message(Command("start"))
async def cmd_start(m: Message):
    uid = str(m.from_user.id)
    if uid not in db["users"]:
        db["users"][uid] = {"url": "None", "type": "views", "amt": 10, "sent": 0}
        save_db()
    
    await m.answer(f"💎 **{get_fancy('turbo booster v2')}**\nStatus: `GOD MODE READY`", 
                   reply_markup=main_menu(uid), parse_mode="Markdown")

@dp.callback_query(F.data == "run")
async def start_turbo(c: CallbackQuery):
    uid = str(c.from_user.id)
    u = db["users"][uid]
    if u["url"] == "None": return await c.answer("❌ Set URL first!", show_alert=True)
    
    msg = await c.message.answer(f"⚡ **{get_fancy('igniting turbo engine')}...**")
    engine = TurboEngine(u["url"], u["type"])
    sem = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    
    done = 0
    total = u["amt"]
    
    async with aiohttp.ClientSession() as session:
        while done < total:
            # Batch creation for concurrency
            remaining = total - done
            batch_size = min(remaining, MAX_CONCURRENT_TASKS)
            
            tasks = [engine.fire_request(session, sem) for _ in range(batch_size)]
            results = await asyncio.gather(*tasks) # Sab ek saath chalenge!
            
            wait_needed = 0
            for status, data in results:
                if status == "OK":
                    done += 1
                    u["sent"] += (500 if u["type"] == "views" else 20)
                    if u["type"] == "views": db["global_stats"]["total_views"] += 500
                    else: db["global_stats"]["total_likes"] += 20
                elif status == "WAIT":
                    wait_needed = max(wait_needed, int(data))
            
            save_db()
            
            # UI Update
            await msg.edit_text(
                f"🚀 **{get_fancy('turbo boosting active')}**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📈 Progress: `{progress_bar(done, total)}`\n"
                f"✅ Batches: `{done}/{total}`\n"
                f"🔥 Speed: `x{MAX_CONCURRENT_TASKS} Turbo`",
                parse_mode="Markdown"
            )

            if wait_needed > 0:
                for i in range(wait_needed, 0, -5):
                    await msg.edit_text(f"⏳ **{get_fancy('cooling down')}**\nResuming in `{i}s`...")
                    await asyncio.sleep(5)
            else:
                await asyncio.sleep(1) # Chhota gap for stability

    await msg.edit_text(f"🏆 **{get_fancy('turbo mission complete')}**\nTotal: `{done}` Batches Delivered!")

# --- ⚙️ HELPERS & UI ---
def main_menu(uid):
    u = db["users"].get(str(uid), {"type": "views", "amt": 10})
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=f"🚀 {get_fancy('start turbo')}", callback_data="run"))
    kb.row(InlineKeyboardButton(text=f"🔗 {get_fancy('url')}", callback_data="set_url"), 
           InlineKeyboardButton(text=f"🔢 {get_fancy('amount')}", callback_data="set_amt"))
    mode_label = "👁️ ᴠɪᴇᴡꜱ" if u['type'] == 'views' else "❤️ ʟɪᴋᴇꜱ"
    kb.row(InlineKeyboardButton(text=f"⚙️ {get_fancy('mode')}: {mode_label}", callback_data="toggle"))
    return kb.as_markup()

@dp.callback_query(F.data == "set_url")
async def ask_url(c: CallbackQuery, state: FSMContext):
    await state.set_state(Setup.waiting_for_url)
    await c.message.answer("🔗 Send Link:")

@dp.message(Setup.waiting_for_url)
async def save_url(m: Message, state: FSMContext):
    if "instagram.com" in m.text:
        db["users"][str(m.from_user.id)]["url"] = m.text
        save_db()
        await m.answer("✅ URL Updated!", reply_markup=main_menu(m.from_user.id))
        await state.clear()

@dp.callback_query(F.data == "toggle")
async def toggle(c: CallbackQuery):
    uid = str(c.from_user.id)
    db["users"][uid]["type"] = "likes" if db["users"][uid]["type"] == "views" else "views"
    save_db()
    await c.message.edit_reply_markup(reply_markup=main_menu(uid))

# Web Health Check
async def handle_health(request): return web.Response(text="Alive")
async def start_web():
    app = web.Application()
    app.router.add_get('/', handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()

async def main():
    asyncio.create_task(start_web())
    print("💎 Turbo Bot Online!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
