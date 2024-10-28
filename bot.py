import os
import requests
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext
)
from telegram.error import TelegramError
from telegram.constants import ParseMode

# Set up your bot token and PostgreSQL database URL
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = "postgres://koyeb-adm:khFat50DlXGj@ep-purple-cloud-a28j7t3o.eu-central-1.pg.koyeb.app/koyebdb"
CHANNEL_USERNAME = "@chatgpt4for_free"  # Replace with your channel username
ENHANCER_API_URL = "https://olivine-tricolor-samba.glitch.me/api/enhancer?url="

# Connect to Koyeb PostgreSQL database
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Initialize database table if not exists
cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        username TEXT,
        verified BOOLEAN DEFAULT FALSE
    )
""")
conn.commit()

# Verification message with buttons
async def send_verification_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_username = context.bot.username
    verification_link = f"https://t.me/{bot_username}?start=verified"
    
    keyboard = [
        [InlineKeyboardButton(
            "I'm not a robot👨‍💼",
            url="https://linkshortify.com/st?api=7d706f6d7c95ff3fae2f2f40cff10abdc0e012e9&url=https://t.me/chatgpt490_bot?start=verified"
        )],
        [InlineKeyboardButton(
            "How to open captcha🔗",
            url="https://t.me/disneysworl_d/5"
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        '♂️ 🅲🅰🅿🆃🅲🅷🅰 ♂️\n\nᴘʟᴇᴀsᴇ ᴠᴇʀɪғʏ ᴛʜᴀᴛ ʏᴏᴜ ᴀʀᴇ ʜᴜᴍᴀɴ 👨‍💼\nᴛᴏ ᴘʀᴇᴠᴇɴᴛ ᴀʙᴜsᴇ ᴡᴇ ᴇɴᴀʙʟᴇᴅ ᴛʜɪs ᴄᴀᴘᴛᴄʜᴀ\n𝗖𝗟𝗜𝗖𝗞 𝗛𝗘𝗥𝗘👇',
        reply_markup=reply_markup 
    )

# Start command with subscription and verification check
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    
    # Check subscription
    try:
        member_status = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member_status.status not in ["member", "administrator", "creator"]:
            await update.message.reply_text(f"Please join our channel {CHANNEL_USERNAME} to use this bot.")
            return
    except TelegramError:
        await update.message.reply_text("Please join our channel to use this bot.")
        return

    # Check or add user in the database
    cur.execute("SELECT verified FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    if user is None:
        cur.execute("INSERT INTO users (user_id, username, verified) VALUES (%s, %s, FALSE)", (user_id, username))
        conn.commit()
    elif not user[0]:  # If user exists but not verified
        await send_verification_message(update, context)
        return

    await update.message.reply_text("Hello! Please send me a photo, and I will enhance it for you.")

# Handle verification status
async def verify_user(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    cur.execute("UPDATE users SET verified = TRUE WHERE user_id = %s", (user_id,))
    conn.commit()
    await update.message.reply_text("Verification successful! You can now use the bot.")

# Handle photos
async def handle_photo(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    cur.execute("SELECT verified FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()

    if user and user[0]:  # Only proceed if user is verified
        photo_file = await update.message.photo[-1].get_file()
        file_url = photo_file.file_path
        api_url = f"{ENHANCER_API_URL}{file_url}"
        await update.message.reply_text("Enhancing your photo, please wait...")

        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            if data["status"] == "success":
                enhanced_image_url = data["image"]
                await update.message.reply_text(f"Here is the enhanced image link: {enhanced_image_url}")
            else:
                await update.message.reply_text("Sorry, something went wrong with the enhancement.")
        else:
            await update.message.reply_text("Failed to connect to the image enhancer API.")
    else:
        await send_verification_message(update, context)

# Broadcast message to all users
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id != 6951715555:  # Replace <ADMIN_ID> with your Telegram ID
        await update.message.reply_text("You are not authorized to use this command.")
        return

    message_text = " ".join(context.args)
    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()
    for user in users:
        try:
            await context.bot.send_message(chat_id=user[0], text=message_text)
        except TelegramError:
            continue
    await update.message.reply_text("Message broadcasted to all users.")

# Command to show total users
async def total_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cur.execute("SELECT COUNT(*) FROM users")
    user_count = cur.fetchone()[0]
    await update.message.reply_text(f"Total users: {user_count}")

# Main function to start the bot with webhook
def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("verify", verify_user))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("total_users", total_users))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Set webhook (replace <YOUR_WEBHOOK_URL> with your actual webhook URL)
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8443)),
        url_path=TELEGRAM_BOT_TOKEN,
        webhook_url=f"https://image-enhancer-ns.onrender.com/{TELEGRAM_BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()
