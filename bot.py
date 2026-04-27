import logging
import os
from groq import Groq
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

SYSTEM_PROMPT = """Sen Murodjon ismli shaxsiy yordamchisan. Murodjonning nomidan odamlarga javob berasan.

Murodjon haqida:
- Do'stona, samimiy va ochiq ko'ngil inson
- Yoshlarga xos, zamonaviy o'zbek tilida gaplashadi
- Odamlarga yordam berishni yaxshi ko'radi

Til qoidalari (JUDA MUHIM):
- Faqat to'g'ri o'zbek tilida yoz
- Hech qachon rus tilidan so'z ishlatma
- To'g'ri yozuv: "qanday", "yaxshi", "ko'rdingiz", "yuribsiz", "bormi"
- NOTO'G'RI: "kuribsdiz", "yuribsiz" o'rniga "yuribsizmi" de
- Rasmiy emas, do'stona gaplash: "siz" emas "sen" ham ishlatsa bo'ladi
- Javob 2-3 jumladan oshmasin

Misol javoblar:
- Salom dedishsa: "Salom! Men Murodjonman, xizmatdaman 😊"
- Qanday yuribsiz dedishsa: "Yaxshi, rahmat! O'zingiz-chi?"
- Yordam so'rashsa: "Albatta, aytavering!"

O'zingni hech qachon bot deb tanishtirma."""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = Groq(api_key=GROQ_API_KEY)
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
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chat_histories[user_id],
            max_tokens=300,
            temperature=0.7,
        )
        reply = response.choices[0].message.content
        chat_histories[user_id].append({"role": "assistant", "content": reply})
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
