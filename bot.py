from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from twilio.rest import Client
import os

# স্টোর ইউজারের লগইন ক্লায়েন্ট
user_clients = {}

# ইউজারের কেনা নাম্বার
user_purchased_numbers = {}

# /start কমান্ড হ্যান্ডলার
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Twilio Bot! Use /login to connect your Twilio account.")

# /login কমান্ড হ্যান্ডলার
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send your Twilio SID.")

# ইউজার টেক্সট পাঠালে হ্যান্ডলার
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id not in user_clients:
        context.user_data["sid"] = text
        await update.message.reply_text("Now send your Twilio Auth Token.")
    elif "sid" in context.user_data and "token" not in context.user_data:
        sid = context.user_data["sid"]
        token = text
        try:
            client = Client(sid, token)
            client.api.accounts(sid).fetch()
            user_clients[user_id] = client
            context.user_data["token"] = token
            await update.message.reply_text("✅ Successfully logged in!")
        except Exception:
            await update.message.reply_text("❌ Invalid SID or Token. Try again with /login.")

# /buy_number: ৫০টি নাম্বার দেখায়
async def buy_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    client = user_clients.get(user_id)
    if not client:
        await update.message.reply_text("⚠️ Please login first using /login.")
        return

    numbers = client.available_phone_numbers("CA").local.list(limit=50)
    if not numbers:
        await update.message.reply_text("❌ No Canadian numbers found.")
        return

    keyboard = [
        [InlineKeyboardButton(n.phone_number, callback_data=f"SELECT:{n.phone_number}")]
        for n in numbers
    ]
    await update.message.reply_text("Choose a number to buy:", reply_markup=InlineKeyboardMarkup(keyboard))

# নাম্বার সিলেক্ট করার পর Buy বাটন দেখানো
async def select_number_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    number = query.data.split("SELECT:")[1]
    keyboard = [[InlineKeyboardButton("Buy 🎉", callback_data=f"CONFIRM_BUY:{number}")]]
    await query.message.reply_text(f"নাম্বার: {number}", reply_markup=InlineKeyboardMarkup(keyboard))

# Buy বাটনে ক্লিক করলে নাম্বার কেনা
async def buy_selected_number_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    number = query.data.split("CONFIRM_BUY:")[1]
    client = user_clients.get(user_id)

    if not client:
        await query.edit_message_text("⚠️ আগে /login করুন।")
        return

    try:
        # আগের নাম্বার থাকলে ডিলিট করো
        existing = client.incoming_phone_numbers.list(limit=1)
        if existing:
            existing[0].delete()

        # নতুন নাম্বার কিনো
        purchased = client.incoming_phone_numbers.create(phone_number=number)
        user_purchased_numbers[user_id] = purchased.phone_number

        keyboard = [[InlineKeyboardButton("Show Messages 🟢", callback_data=f"SHOW_MESSAGES:{number}")]]
        await query.edit_message_text(f"✅ আপনি নাম্বারটি কিনেছেন: {purchased.phone_number}", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await query.edit_message_text("নাম্বার কেনা যায়নি। আপনার আগের নাম্বার ডিলিট করে আবার চেষ্টা করুন।")

# Show Messages বাটন হ্যান্ডলার
async def show_messages_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    client = user_clients.get(user_id)

    if not client:
        await query.edit_message_text("⚠️ আগে /login করুন।")
        return

    try:
        messages = client.messages.list(limit=20)
        incoming = [m for m in messages if m.direction == "inbound"]
        if not incoming:
            await query.edit_message_text("কোনো Incoming Message পাওয়া যায়নি।")
            return

        output = "\n\n".join([f"From: {m.from_}\nTo: {m.to}\nBody: {m.body}" for m in incoming[:5]])
        await query.edit_message_text(output)
    except Exception as e:
        await query.edit_message_text("মেসেজ আনতে সমস্যা হয়েছে।")

# বট চালানোর ফাংশন
def main():
    token = os.getenv("8058100416:AAHxtVSOadxiyhXYMCVT748pZqQcdqDk-84")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("buy_number", buy_number))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(select_number_handler, pattern="^SELECT:"))
    app.add_handler(CallbackQueryHandler(buy_selected_number_handler, pattern="^CONFIRM_BUY:"))
    app.add_handler(CallbackQueryHandler(show_messages_handler, pattern="^SHOW_MESSAGES:"))

    app.run_polling()

if __name__ == "__main__":
    main()
