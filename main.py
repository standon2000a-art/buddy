import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)
from groq import Groq

# .env fayldan yuklash (lokal uchun)
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PORT = int(os.getenv("PORT", 8000))

# Groq client
client = Groq(api_key=GROQ_API_KEY)

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Har bir foydalanuvchi uchun chat tarixi
chat_histories = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_histories[user.id] = []
    await update.message.reply_text(
        f"Salom, {user.first_name}! 👋\n\n"
        "Men Groq AI botman. Menga istalgan savolingizni yozing.\n\n"
        "📌 /clear - Suhbat tarixini tozalash\n"
        "📌 /help  - Yordam"
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_histories[user_id] = []
    await update.message.reply_text("🗑 Suhbat tarixi tozalandi!")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot buyruqlari:\n\n"
        "/start - Botni qayta ishga tushirish\n"
        "/clear - Suhbat tarixini tozalash\n"
        "/help  - Yordam\n\n"
        "Oddiy xabar yozsangiz, AI javob beradi!"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    if user_id not in chat_histories:
        chat_histories[user_id] = []

    chat_histories[user_id].append({"role": "user", "content": user_text})

    if len(chat_histories[user_id]) > 20:
        chat_histories[user_id] = chat_histories[user_id][-20:]

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Sen yordamchi AI assistantsan. Foydalanuvchiga qisqa, aniq va foydali javoblar ber. O'zbek tilida so'ralsa o'zbekcha javob ber.",
                },
            ]
            + chat_histories[user_id],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=2048,
        )

        ai_response = chat_completion.choices[0].message.content
        chat_histories[user_id].append({"role": "assistant", "content": ai_response})

        if len(ai_response) > 4096:
            for i in range(0, len(ai_response), 4096):
                await update.message.reply_text(ai_response[i : i + 4096])
        else:
            await update.message.reply_text(ai_response)

    except Exception as e:
        logger.error(f"Xatolik: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi. Keyinroq urinib ko'ring.")


def main():
    if not TELEGRAM_TOKEN or not GROQ_API_KEY:
        print("❌ XATO: TELEGRAM_TOKEN yoki GROQ_API_KEY topilmadi!")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print(f"✅ Bot webhook rejimida ishga tushdi (port: {PORT})...")

    # Webhook rejimi — Koyeb uchun
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=os.getenv("WEBHOOK_URL", ""),
    )


if __name__ == "__main__":
    main()