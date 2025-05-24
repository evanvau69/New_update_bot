from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
from twilio.rest import Client

# In-memory session and user number tracking
user_sessions = {}
user_numbers = {}

# Login command
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sid = context.args[0]
        auth_token = context.args[1]
        client = Client(sid, auth_token)
        client.api.accounts(sid).fetch()

        user_sessions[update.effective_user.id] = {
            "sid": sid,
            "auth_token": auth_token
        }

        await update.message.reply_text("✅ লগইন সফল হয়েছে!")
    except Exception as e:
        await update.message.reply_text("❌ লগইন ব্যর্থ। SID অথবা AUTH TOKEN ভুল।")

# Helper function to get Twilio client
def get_twilio_client(user_id):
    session = user_sessions.get(user_id)
    if session:
        return Client(session["sid"], session["auth_token"])
    return None

# Buy number command
async def buy_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    client = get_twilio_client(user_id)
    if not client:
        await update.message.reply_text("❗️আপনি এখনো লগইন করেননি। /login দিয়ে লগইন করুন।")
        return

    numbers = client.available_phone_numbers("CA").local.list(limit=50)

    keyboard = [
        [InlineKeyboardButton(num.phone_number, callback_data=f"select_{num.phone_number}")]
        for num in numbers
    ]
    markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("🇨🇦 নিচে কানাডিয়ান নাম্বার লিস্ট:", reply_markup=markup)

# Callback for number selection and buy
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    client = get_twilio_client(user_id)
    if not client:
        await query.edit_message_text("❗️আপনি লগইন করেননি।")
        return

    data = query.data

    if data.startswith("select_"):
        phone_number = data.split("_")[1]
        keyboard = [
            [InlineKeyboardButton("Buy 🎉", callback_data=f"buy_{phone_number}")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(f"নাম্বার: {phone_number}", reply_markup=markup)

    elif data.startswith("buy_"):
        new_number = data.split("_")[1]

        # Delete old number if exists
        if user_id in user_numbers:
            try:
                old_sid = user_numbers[user_id]
                client.incoming_phone_numbers(old_sid).delete()
                await query.message.reply_text("❌ আগের নাম্বার ডিলিট করা হয়েছে।")
            except:
                await query.message.reply_text("⚠️ পুরনো নাম্বার ডিলিট করতে সমস্যা হয়েছে।")

        # Buy new number
        incoming_number = client.incoming_phone_numbers.create(phone_number=new_number)
        user_numbers[user_id] = incoming_number.sid

        await query.message.reply_text(f"✅ আপনি নাম্বারটি কিনেছেন: {new_number}")

# Show incoming messages
async def show_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    client = get_twilio_client(user_id)

    if not client:
        await update.message.reply_text("❗️আপনি লগইন করেননি।")
        return

    if user_id not in user_numbers:
        await update.message.reply_text("❗️আপনার কোনো নাম্বার অ্যাক্টিভ নেই।")
        return

    phone_sid = user_numbers[user_id]
    number = client.incoming_phone_numbers(phone_sid).phone_number

    messages = client.messages.list(to=number, limit=10)
    if not messages:
        await update.message.reply_text("কোনো ইনকামিং মেসেজ পাওয়া যায়নি।")
        return

    text = f"📨 Incoming messages for {number}:\n\n"
    for msg in messages:
        text += f"From: {msg.from_}\nBody: {msg.body}\n\n"

    await update.message.reply_text(text)

# Bot start
app = ApplicationBuilder().token("7920919744:AAFDXdbj8OB68YsgxqdPaf3FwKPgUNbQmnM").build()

app.add_handler(CommandHandler("login", login))
app.add_handler(CommandHandler("buy_number", buy_number))
app.add_handler(CommandHandler("show", show_messages))
app.add_handler(CallbackQueryHandler(button_handler))

app.run_polling()
