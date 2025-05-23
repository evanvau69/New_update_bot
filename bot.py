# bot.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from twilio.rest import Client
from session_store import save_session, get_session

logging.basicConfig(level=logging.INFO)

# --- Start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /login <SID> <AUTH_TOKEN> to begin.")

# --- Login Command ---
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Use: /login <SID> <AUTH_TOKEN>")
        return
    sid, token = context.args
    try:
        client = Client(sid, token)
        client.api.accounts(sid).fetch()  # test login
        save_session(update.effective_user.id, sid, token)
        await update.message.reply_text("✅ Logged in successfully!")
    except Exception as e:
        await update.message.reply_text(f"Login failed: {e}")

# --- Buy Number Command ---
async def buy_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = get_session(update.effective_user.id)
    if not session:
        await update.message.reply_text("Please login first using /login")
        return

    client = Client(session["sid"], session["token"])
    numbers = client.available_phone_numbers("CA").local.list(limit=50)

    for number in numbers:
        button = InlineKeyboardButton("Buy", callback_data=f"buy|{number.phone_number}")
        markup = InlineKeyboardMarkup([[button]])
        await update.message.reply_text(f"{number.phone_number}", reply_markup=markup)

# --- Handle Buy Button ---
async def handle_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, phone_number = query.data.split("|")
    user_id = query.from_user.id
    session = get_session(user_id)

    if action == "buy":
        try:
            client = Client(session["sid"], session["token"])
            client.incoming_phone_numbers.create(phone_number=phone_number)
            new_button = InlineKeyboardButton("Show Messages 🟢", callback_data=f"show|{phone_number}")
            markup = InlineKeyboardMarkup([[new_button]])
            await query.edit_message_text(f"✅ Bought number: {phone_number}", reply_markup=markup)
        except Exception as e:
            await query.edit_message_text(f"❌ Failed to buy: {e}")

# --- Handle Show Messages Button ---
async def handle_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, phone_number = query.data.split("|")
    session = get_session(query.from_user.id)

    if action == "show":
        client = Client(session["sid"], session["token"])
        messages = client.messages.list(to=phone_number, limit=10)
        if not messages:
            await query.edit_message_text(f"No messages yet for {phone_number}")
        else:
            text = f"Messages for {phone_number}:\n\n"
            for msg in messages:
                text += f"From: {msg.from_}\n{msg.body}\n\n"
            await query.edit_message_text(text)

# --- Main Function ---
def main():
    TOKEN = "8058100416:AAHxtVSOadxiyhXYMCVT748pZqQcdqDk-84"
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("buy_number", buy_number))
    app.add_handler(CallbackQueryHandler(handle_buy, pattern="^buy\\|"))
    app.add_handler(CallbackQueryHandler(handle_show, pattern="^show\\|"))

    app.run_polling()

if __name__ == "__main__":
    main()
