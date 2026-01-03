import asyncio
import json
import os
import uuid
import aiohttp
from aiohttp import web

# --- 🛠 CONFIGURATION (Loads from your config.json) ---
def load_config():
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            return json.load(f)
    return {"video_url": "None", "amount_of_boosts": 10}

config = load_config()
TARGET_URL = config.get("video_url")
# [span_2](start_span)Render sets the PORT environment variable automatically[span_2](end_span)
PORT = int(os.environ.get("PORT", 8080)) 

# -[span_3](start_span)-- 🌐 HTTP SERVER FOR RENDER (Keeps the service alive)[span_3](end_span) ---
async def handle_health_check(request):
    return web.Response(text="Bot is Alive and Running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

# -[span_4](start_span)-- ⚡ ZEFAME API ENGINE (Pure Logic from your files)[span_4](end_span) ---
class ZefameEngine:
    def __init__(self, url, s_type='views'):
        self.url = url
        # [span_5](start_span)service 237 for views, 234 for likes[span_5](end_span)
        self.service_id = 237 if s_type == 'views' else 234 
        [span_6](start_span)self.endpoint = "https://zefame-free.com/api_free.php?action=order"[span_6](end_span)
    
    async def request_boost(self):
        try:
            # [span_7](start_span)Splits URL to get postId[span_7](end_span)
            pid = self.url.split("/")[4] if "/" in self.url else "" 
            async with aiohttp.ClientSession() as session:
                # [span_8](start_span)Data structure exactly as per your requirement[span_8](end_span)
                data = {
                    "service": self.service_id, 
                    "link": self.url, 
                    "uuid": str(uuid.uuid4()), 
                    "postId": pid
                }
                async with session.post(self.endpoint, data=data, timeout=15) as r:
                    res = await r.json()
                    # [span_9](start_span)Handling success and cooldowns[span_9](end_span)
                    if res.get('success'): 
                        return "OK", None
                    if 'timeLeft' in str(res): 
                        return "WAIT", res['data']['timeLeft']
        except Exception as e: 
            return "ERR", str(e)
        return "FAIL", "Unknown"

# --- 🚀 AUTOMATIC EXECUTION LOOP ---
async def run_auto_boost():
    if not TARGET_URL or TARGET_URL == "None":
        print("❌ Error: No URL found in config.json")
        return

    print(f"🛰️ INITIATING SERVER CONNECTION...")
    print(f"🎯 Target URL: {TARGET_URL}")
    
    engine = ZefameEngine(TARGET_URL, 'views')
    done = 0
    total_needed = config.get("amount_of_boosts", 999999)

    while done < total_needed:
        status, data = await engine.request_boost()
        
        if status == "OK":
            done += 1
            print(f"✅ BATCH {done} COMPLETED SUCCESSFULLY!")
            # [span_10](start_span)5-second delay to prevent bans[span_10](end_span)
            await asyncio.sleep(5) 
            
        elif status == "WAIT":
            # [span_11](start_span)Handles API cooldown using timeLeft from response[span_11](end_span)
            print(f"⏳ API LIMIT! WAITING {data} SECONDS...")
            await asyncio.sleep(int(data))
            
        else:
            print(f"⚠️ ERROR: {data}. RETRYING IN 10 SECONDS...")
            await asyncio.sleep(10)

# --- 🏁 MAIN ENTRY POINT ---
async def main():
    # Starts both the health check server and the booster loop simultaneously
    await asyncio.gather(
        start_web_server(),
        run_auto_boost()
    )

if __name__ == "__main__":
    print("💎 Premium Insta-Booster is Online (Auto-Mode)!")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user.")
        
