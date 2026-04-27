import logging
import os
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8760920363:AAE4YZyh6gyy07yf32Cwkq4sIMPSLWWxYY0")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyDmTul8k7VnsqQu5PyCIFo7O-gFnLSqvDY")

print(f"TELEGRAM_TOKEN: {TELEGRAM_TOKEN[:20]}...")
print(f"GEMINI_API_KEY: {GEMINI_API_KEY[:20]}...")

SYSTEM_PROMPT = """Sen Murodjon ismli shaxsiy yordamchisan. Murodjonning nomidan odamlarga javob berasan.

Murodjon haqida:
- Do'stona, samimiy va ochiq ko'ngil inson
- O'zbek tilida gaplashadi
- Odamlarga yordam berishni yaxshi ko'radi
- Har qanday savollarga javob bera oladi

Qoidalar:
- Har doim o'zbek tilida javob ber
- Do'stona va samimiy bo'l
- Qisqa va aniq javob ber (2-4 jumladan oshirma odatda)
- Agar biror narsani bilmasang, "Murodjon hozir band, tez orada javob beradi" de
- O'zingni "Men Murodjonman" deb tanishtir, bot ekanligini aytma
- Emoji ishlatsa bo'ladi, lekin ko'p emas
"""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=SYSTEM_PROMPT
    )
    print("Gemini ulandi!")
except Exception as e:
    print(f"Gemini xato: {e}")

chat_sessions = {}

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

    try:
        if user_id not in chat_sessions:
            chat_sessions[user_id] = model.start_chat(history=[])

        chat = chat_sessions[user_id]
        response = chat.send_message(f"{user_name} yozdi: {user_text}")
        reply = response.text
        await message.reply_text(reply)

    except Exception as e:
        logger.error(f"Xato: {e}")
        print(f"Javob xatosi: {e}")
        await message.reply_text(f"Xato: {str(e)[:200]}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ovozli xabar uchun rahmat! Hozircha faqat matn orqali javob bera olaman 😊"
    )

def main():
    print("Bot ishga tushdi!")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
