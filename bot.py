import logging
import os
import json
from datetime import datetime, timedelta
from groq import Groq
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GOOGLE_TOKEN = os.environ.get("GOOGLE_TOKEN", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

groq_client = Groq(api_key=GROQ_API_KEY)

def get_calendar_service():
    try:
        token_data = json.loads(GOOGLE_TOKEN)
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes"),
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        service = build("calendar", "v3", credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Calendar xato: {e}")
        return None

def get_upcoming_events(days=7):
    try:
        service = get_calendar_service()
        if not service:
            return "Calendar ulanmadi"
        now = datetime.utcnow().isoformat() + "Z"
        end = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"
        events_result = service.events().list(
            calendarId="primary", timeMin=now, timeMax=end,
            maxResults=10, singleEvents=True, orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])
        if not events:
            return "Yaqin kunlarda voqealar yo'q"
        result = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            try:
                dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                formatted = dt.strftime("%d-%m %H:%M")
            except:
                formatted = start
            result.append(f"• {formatted} — {event.get('summary', 'Noma\\'lum')}")
        return "\n".join(result)
    except Exception as e:
        return f"Xato: {e}"

def add_calendar_event(title, date_str, time_str="10:00"):
    try:
        service = get_calendar_service()
        if not service:
            return "Calendar ulanmadi"
        dt_str = f"{date_str}T{time_str}:00"
        dt = datetime.fromisoformat(dt_str)
        dt_end = dt + timedelta(hours=1)
        event = {
            "summary": title,
            "start": {"dateTime": dt.isoformat(), "timeZone": "Asia/Tashkent"},
            "end": {"dateTime": dt_end.isoformat(), "timeZone": "Asia/Tashkent"},
        }
        service.events().insert(calendarId="primary", body=event).execute()
        return f"✅ '{title}' qo'shildi — {date_str} {time_str}"
    except Exception as e:
        return f"Xato: {e}"

SYSTEM_PROMPT = """Sen Murodjon ismli shaxsiy yordamchisan. Murodjonning nomidan odamlarga javob berasan.

Murodjon haqida:
- Do'stona, samimiy va ochiq ko'ngil inson
- Yoshlarga xos, zamonaviy o'zbek tilida gaplashadi
- Odamlarga yordam berishni yaxshi ko'radi

Qobiliyatlaring:
- Google Calendar: uchrashuvlar ko'rish va qo'shish
- Har qanday savolga javob berish

Til qoidalari:
- Faqat to'g'ri o'zbek tilida yoz
- Do'stona va qisqa gaplash (2-3 jumla)
- O'zingni bot deb tanishtirma

Buyruqlarni aniqlash:
- "Kalendar", "jadval", "uchrashuv kor" = CALENDAR_VIEW
- "Qosh", "yoz", "belgilab qoy" + sana = CALENDAR_ADD: sarlavha | sana(YYYY-MM-DD) | vaqt(HH:MM)

Javob formatlar:
- Oddiy savol: oddiy javob
- Kalendar so'rasa: CALENDAR_VIEW
- Voqea qo'shish: CALENDAR_ADD: sarlavha | sana | vaqt"""

chat_histories = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "do'stim"
    message = update.message

    if not message.text:
        await message.reply_text("Hozircha faqat matn xabarlariga javob bera olaman 😊")
        return

    user_text = message.text
    logger.info(f"[{user_name}]: {user_text}")

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if user_id not in chat_histories:
        chat_histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    chat_histories[user_id].append({"role": "user", "content": user_text})

    if len(chat_histories[user_id]) > 20:
        chat_histories[user_id] = [chat_histories[user_id][0]] + chat_histories[user_id][-19:]

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chat_histories[user_id],
            max_tokens=400,
            temperature=0.7,
        )
        reply = response.choices[0].message.content
        chat_histories[user_id].append({"role": "assistant", "content": reply})

        if "CALENDAR_VIEW" in reply:
            events = get_upcoming_events()
            await message.reply_text(f"📅 Yaqin 7 kunlik jadval:\n\n{events}")
        elif "CALENDAR_ADD:" in reply:
            try:
                parts = reply.split("CALENDAR_ADD:")[1].strip().split("|")
                title = parts[0].strip()
                date = parts[1].strip()
                time = parts[2].strip() if len(parts) > 2 else "10:00"
                result = add_calendar_event(title, date, time)
                await message.reply_text(result)
            except:
                await message.reply_text(reply)
        else:
            await message.reply_text(reply)

    except Exception as e:
        logger.error(f"Xato: {e}")
        await message.reply_text("Hozir band ekanman, bir ozdan keyin yozing 🙏")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ovozli xabar uchun rahmat! Matn orqali yozsangiz javob beraman 😊")

def main():
    print("Bot ishga tushdi!")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
