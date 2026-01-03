import asyncio
import json
import os
import uuid
import aiohttp
from aiohttp import web

# --- 🛠 CONFIGURATION (Config.json se data lena) ---
def load_config():
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            return json.load(f)
    return {"video_url": "None", "amount_of_boosts": 10}

config = load_config()
TARGET_URL = config.get("video_url")
# [span_1](start_span)Render automatic port set karta hai[span_1](end_span)
PORT = int(os.environ.get("PORT", 8080)) 

# --- 🌐 HTTP SERVER FOR RENDER (Bot ko active rakhne ke liye) ---
async def handle_health_check(request):
    return web.Response(text="Bot is Alive and Running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

# --- ⚡ ZEFAME API ENGINE (Source logic) ---
class ZefameEngine:
    def __init__(self, url, s_type='views'):
        self.url = url
        # [span_2](start_span)Views ke liye 237, Likes ke liye 234[span_2](end_span)
        self.service_id = 237 if s_type == 'views' else 234 
        [span_3](start_span)self.endpoint = "https://zefame-free.com/api_free.php?action=order"[span_3](end_span)
    
    async def request_boost(self):
        try:
            # [span_4](start_span)URL se postId nikalna[span_4](end_span)
            pid = self.url.split("/")[4] if "/" in self.url else "" 
            async with aiohttp.ClientSession() as session:
                # [span_5](start_span)Data dictionary wahi hai jo aapne bheja tha[span_5](end_span)
                data = {
                    "service": self.service_id, 
                    "link": self.url, 
                    "uuid": str(uuid.uuid4()), 
                    "postId": pid
                }
                async with session.post(self.endpoint, data=data, timeout=15) as r:
                    res = await r.json()
                    if res.get('success'): 
                        return "OK", None
                    if 'timeLeft' in str(res): 
                        return "WAIT", res['data']['timeLeft']
        except: 
            return "ERR", "Connection Timeout"
        return "FAIL", "Unknown"

# --- 🚀 AUTOMATED LOOP (Direct Server par chalega) ---
async def run_auto_boost():
    if not TARGET_URL or TARGET_URL == "None":
        print("❌ Error: config.json mein URL nahi mila!")
        return

    print(f"🛰️ Server start ho gaya hai...")
    print(f"🎯 Target URL: {TARGET_URL}")
    
    engine = ZefameEngine(TARGET_URL, 'views')
    done = 0
    # [span_6](start_span)Config se boost amount lena[span_6](end_span)
    total_needed = config.get("amount_of_boosts", 999999)

    while done < total_needed:
        status, data = await engine.request_boost()
        
        if status == "OK":
            done += 1
            print(f"✅ Kaam chalu hai: {done} batches pure huye.")
            [span_7](start_span)await asyncio.sleep(5) # Thoda delay taaki spam na ho[span_7](end_span)
            
        elif status == "WAIT":
            # [span_8](start_span)Agar API limit aaye toh wait karna[span_8](end_span)
            print(f"⏳ Limit aa gayi! {data} seconds wait kar raha hoon...")
            await asyncio.sleep(int(data))
            
        else:
            print("⚠️ Error! 10 second mein dobara koshish karenge...")
            await asyncio.sleep(10)

# --- 🏁 MAIN EXECUTION ---
async def main():
    # HTTP server aur Automation dono ek saath start honge
    await asyncio.gather(
        start_web_server(),
        run_auto_boost()
    )

if __name__ == "__main__":
    print("💎 Insta-Booster Direct Mode Online!")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot band ho gaya.")
        
