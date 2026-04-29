from skyfield.api import load, EarthSatellite
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import math
import os

# ====== NEW GEMINI SDK (FIXED) ======
from google import genai

# ====== TOKENS ======
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ====== GEMINI SETUP (FIXED) ======
client = genai.Client(api_key=GEMINI_API_KEY)

# ====== SATELLITE ======
line1 = "1 43678U 18084H   26071.99099230  .00005079  00000-0  41314-3 0  9993"
line2 = "2 43678  98.1041 264.1630 0012149 116.9049 243.3416 14.99984619401796"
name = "DIWATA-2"

ts = load.timescale()
sat = EarthSatellite(line1, line2, name, ts)

# ====== USER MEMORY ======
user_data_store = {}

# ====== GET SATELLITE DATA ======
def get_satellite_data():
    t = ts.now()
    geo = sat.at(t)
    sub = geo.subpoint()

    velocity = geo.velocity.km_per_s
    speed = (velocity[0]**2 + velocity[1]**2 + velocity[2]**2) ** 0.5

    return {
        "lat": sub.latitude.degrees,
        "lon": sub.longitude.degrees,
        "alt": sub.elevation.km,
        "speed": speed,
        "time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }

# ====== COMMAND: /satellite ======
async def satellite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_satellite_data()
    user_id = update.effective_user.id

    user_data_store[user_id] = {
        "data": data,
        "context": f"""
Satellite: {name}
Latitude: {data['lat']}
Longitude: {data['lon']}
Altitude: {data['alt']} km
Speed: {data['speed']} km/s
Time: {data['time']}
"""
    }

    message = (
        f"🚀 {name}\n"
        f"🕒 {data['time']} UTC\n"
        f"----------------------\n"
        f"📍 Lat: {data['lat']:.4f}\n"
        f"📍 Lon: {data['lon']:.4f}\n"
        f"📏 Alt: {data['alt']:.2f} km\n"
        f"💨 Speed: {data['speed']:.4f} km/s\n\n"
        f"click /diwata2 to get more data\n\n"
        f"Ask anything"
    )

    await update.message.reply_text(message)

# ====== MESSAGE HANDLER (FIXED GEMINI ONLY) ======
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.lower()

    user_info = user_data_store.get(user_id)

    if not user_info:
        await update.message.reply_text("⚠️ Use /satellite first.")
        return

    data = user_info["data"]
    context_data = user_info["context"]

    user_lat = 13.7563
    user_lon = 100.5018

    distance = math.sqrt(
        (data["lat"] - user_lat)**2 +
        (data["lon"] - user_lon)**2
    ) * 111

    small_talk = ["ok", "thanks", "thank you", "lol", "nice", "cool"]

    if text in small_talk:
        prompt = f"""
User: {text}
Reply naturally and briefly.
"""
    else:
        prompt = f"""
You are a satellite (DIWATA-2) expert AI.

Latest satellite data:
{context_data}

User location:
Latitude: {user_lat}
Longitude: {user_lon}
Distance to satellite: {distance:.2f} km

User question: {text}

Rules:
- "it", "this", "that" refer to the satellite data above
- Explain clearly and simply
- If user asks "above me", use distance
- Keep answers short and natural
"""

    # ====== FIXED GEMINI CALL ======
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        await update.message.reply_text(response.text)

    except Exception as e:
        await update.message.reply_text(f"❌ AI Error: {e}")

# ====== START ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
👋 Welcome to DIWATA-2 Satellite AI Tracker!

What you can do:
- Click /diwata2 → get live satellite data
- Ask questions like:
  • "what is it?"
  • "explain"
  • "is it above me?"
  • "what are those data?"

I will explain satellite data using AI in simple terms.

— Designed by Andrew (Zay Bhone Aung).
"""

    await update.message.reply_text(welcome_text)

# ====== MAIN ======
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("diwata2", satellite))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🤖 Smart Satellite AI Bot running...")

app.run_polling(drop_pending_updates=True)
