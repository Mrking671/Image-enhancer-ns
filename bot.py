import os
import requests
import logging
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)
from pymongo import MongoClient
from datetime import datetime, timedelta

# Environment Variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # Channel ID for force subscription
ADMIN_ID = os.getenv("ADMIN_ID")  # Admin ID for broadcasting and total users command

# MongoDB Setup
client = MongoClient(MONGODB_URI)
db = client['telegram_bot']
users_collection = db['users']

# Logger setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Helper function to check subscription status
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
    return member.status in ["member", "administrator", "creator"]

# Helper function to check if user is verified within the last 12 hours
def is_verified_recently(user_id: int) -> bool:
    user_data = users_collection.find_one({"user_id": user_id})
    if user_data and user_data.get("verified") and datetime.utcnow() - user_data["last_verified"] < timedelta(hours=12):
        return True
    return False

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    # Check if user came back from verification link
    if context.args and context.args[0] == "verified":
        await auto_verify(update, context)
        return

    # Check subscription status
    if not await check_subscription(user.id, context):
        await update.message.reply_text(
            "Please subscribe to our channel to use this bot.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Subscribe", url=f"https://t.me/{CHANNEL_ID}")]]
            )
        )
        return

    # Verification reminder if user is not recently verified
    if not is_verified_recently(user.id):
        await update.message.reply_text(
            "Please verify that you are human by clicking the button below.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("I'm not a robot", url="https://t.me/Image_enhancerremini_bot?start=verified")]]
            )
        )
    else:
        await update.message.reply_text("Welcome back! You’re verified and can use the bot.")

# Auto-verify user on return from verification link
async def auto_verify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    now = datetime.utcnow()

    # Update verification status for 12 hours
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"verified": True, "last_verified": now}},
        upsert=True
    )

    await update.message.reply_text("You are now verified and can use the bot!")

# Handle Photos for Enhancement
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if not await check_subscription(user_id, context):
        await update.message.reply_text("Please subscribe to our channel to use this bot.")
        return

    if not is_verified_recently(user_id):
        await update.message.reply_text(
            "Please verify that you are human by clicking the button below.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("I'm not a robot", url="https://t.me/Image_enhancerremini_bot?start=verified")]]
            )
        )
        return

    # Processing the photo
    photo_file = await update.message.photo[-1].get_file()
    file_url = photo_file.file_path

    api_url = f"https://olivine-tricolor-samba.glitch.me/api/enhancer?url={file_url}"
    await update.message.reply_text("Enhancing your photo, please wait...")

    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "success":
            enhanced_image_url = data["image"]
            enhanced_image_data = requests.get(enhanced_image_url)

            if enhanced_image_data.status_code == 200:
                with open("enhanced_image.png", "wb") as f:
                    f.write(enhanced_image_data.content)
                with open("enhanced_image.png", "rb") as f:
                    await update.message.reply_document(document=InputFile(f), caption="Here is your enhanced image!")
            else:
                await update.message.reply_text("Failed to download the enhanced image.")
        else:
            await update.message.reply_text("Enhancement failed.")
    else:
        await update.message.reply_text("Failed to connect to the enhancement service.")

# Broadcast command for admin
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != int(ADMIN_ID):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Please provide a message to broadcast.")
        return

    # Broadcast to all verified users
    users = users_collection.find({"verified": True})
    for user in users:
        try:
            await context.bot.send_message(chat_id=user['user_id'], text=text)
        except Exception as e:
            logger.warning(f"Failed to send message to {user['user_id']}: {e}")

    await update.message.reply_text("Broadcast completed.")

# Command to show total users
async def total_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != int(ADMIN_ID):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    total_count = users_collection.count_documents({})
    await update.message.reply_text(f"Total users: {total_count}")

# Webhook Configuration
def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("total_users", total_users))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Webhook Setup
    PORT = int(os.environ.get("PORT", 8443))
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TELEGRAM_BOT_TOKEN,
        webhook_url=f"https://image-enhancer-ns.onrender.com/{TELEGRAM_BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()
