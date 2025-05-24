import os
from flask import Flask, request
from twilio.rest import Client
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
from telegram.ext.webhook import WebhookServer

TOKEN = os.getenv("7920919744:AAFDXdbj8OB68YsgxqdPaf3FwKPgUNbQmnM")
APP_URL = os.getenv("https://new-update-bot.onrender.com")  # Ex: https://your-service.onrender.com

# Memory-based user data
user_sessions = {}
user_numbers = {}

# Flask app init
flask_app = Flask(__name__)

# Telegram App init
telegram_app = Application.builder().token(TOKEN).build()

# Helper to get client
def get_twilio_client(user_id):
    session = user_sessions.get(user_id)
    if session:
        return Client(session["sid"], session["auth_token"])
    return None

# Login command
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sid = context.args[0]
        token = context.args[1]
        client = Client(sid, token)
        client.api.accounts(sid).fetch()
        user_sessions[update.effective_user.id] = {"sid": sid, "auth_token": token}
        await update.message.reply_text("✅ লগইন সফল হয়েছে!")
    except:
        await update.message.reply_text("❌ লগইন ব্যর্থ। SID বা Token ভুল।")

# Buy number
async def buy_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    client = get_twilio_client(user_id)
    if not client:
        await update.message.reply_text("❗️আপনি লগইন করেননি।")
        return
    numbers = client.available_phone_numbers("CA").local.list(limit=50)
    keyboard = [[InlineKeyboardButton(num.phone_number, callback_data=f"select_{num.phone_number}")] for num in numbers]
    await update.message.reply_text("🇨🇦 কানাডিয়ান নাম্বার লিস্ট:", reply_markup=InlineKeyboardMarkup(keyboard))

# Show messages
async def show_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    client = get_twilio_client(user_id)
    if not client or user_id not in user_numbers:
        await update.message.reply_text("❗️আপনার কোনো একটিভ নাম্বার নেই।")
        return
    sid = user_numbers[user_id]
    number = client.incoming_phone_numbers(sid).phone_number
    messages = client.messages.list(to=number, limit=10)
    if not messages:
        await update.message.reply_text("কোনো ইনকামিং মেসেজ নেই।")
        return
    text = f"📨 মেসেজ (for {number}):\n\n"
    for msg in messages:
        text += f"From: {msg.from_}\nBody: {msg.body}\n\n"
    await update.message.reply_text(text)

# Callback handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    client = get_twilio_client(user_id)
    if not client:
        await query.edit_message_text("❗️লগইন করুন।")
        return
    data = query.data
    if data.startswith("select_"):
        number = data.split("_", 1)[1]
        keyboard = [[InlineKeyboardButton("Buy 🎉", callback_data=f"buy_{number}")]]
        await query.message.reply_text(f"নাম্বার: {number}", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("buy_"):
        number = data.split("_", 1)[1]
        if user_id in user_numbers:
            try:
                old_sid = user_numbers[user_id]
                client.incoming_phone_numbers(old_sid).delete()
                await query.message.reply_text("❌ পুরাতন নাম্বার ডিলিট হয়েছে।")
            except:
                await query.message.reply_text("⚠️ আগের নাম্বার ডিলিট করতে সমস্যা হয়েছে।")
        incoming = client.incoming_phone_numbers.create(phone_number=number)
        user_numbers[user_id] = incoming.sid
        await query.message.reply_text(f"✅ আপনি কিনেছেন: {number}")

# Register handlers
telegram_app.add_handler(CommandHandler("login", login))
telegram_app.add_handler(CommandHandler("buy_number", buy_number))
telegram_app.add_handler(CommandHandler("show", show_messages))
telegram_app.add_handler(CallbackQueryHandler(button_handler))

# Flask route for webhook
@flask_app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    telegram_app.update_queue.put(update)
    return "OK"

# Set webhook when app starts
@flask_app.before_first_request
def set_webhook():
    telegram_app.bot.set_webhook(f"{APP_URL}/webhook/{TOKEN}")

# Start app
if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=10000)
