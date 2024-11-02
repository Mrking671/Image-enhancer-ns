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
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# MongoDB Setup
client = MongoClient(MONGODB_URI)
db = client['telegram_bot']
users_collection = db['users']

# Enhance API endpoint
ENHANCER_API_URL = "https://olivine-tricolor-samba.glitch.me/api/enhancer?url="

# Logger setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Helper function to check subscription status
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
    return member.status in ["member", "administrator", "creator"]

# Helper function to check recent verification status (within 12 hours)
def is_verified_recently(user_id: int) -> bool:
    user_data = users_collection.find_one({"user_id": user_id})
    if user_data and "last_verified" in user_data:
        return datetime.utcnow() - user_data["last_verified"] < timedelta(hours=12)
    return False

# Force Subscription & Auto-Verification
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not await check_subscription(user.id, context):
        await update.message.reply_text(
            "Please subscribe to our channel to use this bot.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Subscribe", url=f"https://t.me/{CHANNEL_ID}")]]
            )
        )
        return

    # Auto-Verify if accessed via link
    if update.message.text == "/start verified":
        users_collection.update_one(
            {"user_id": user.id},
            {"$set": {"user_id": user.id, "verified": True, "last_verified": datetime.utcnow()}},
            upsert=True
        )
        await update.message.reply_text("You are verified! You can now use the bot.")
    elif not is_verified_recently(user.id):
        await send_verification_message(update)
    else:
        await update.message.reply_text("Welcome back! You’re verified and can use the bot.")

# Send verification message if needed
async def send_verification_message(update: Update) -> None:
    keyboard = [
        [InlineKeyboardButton("I'm not a robot", url="https://t.me/Image_enhancerremini_bot?start=verified")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Please verify that you are human by clicking the button below.",
        reply_markup=reply_markup
    )

# Broadcast message to all verified users
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Please provide a message to broadcast.")
        return

    users = users_collection.find({"verified": True})
    for user in users:
        try:
            await context.bot.send_message(chat_id=user['user_id'], text=text)
        except Exception as e:
            logger.warning(f"Failed to send message to {user['user_id']}: {e}")

    await update.message.reply_text("Broadcast completed.")

# Command to show total verified users
async def total_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    total_count = users_collection.count_documents({"verified": True})
    await update.message.reply_text(f"Total verified users: {total_count}")

# Handle Photos for Enhancement
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if not await check_subscription(user_id, context):
        await update.message.reply_text("Please subscribe to our channel to use this bot.")
        return

    if not is_verified_recently(user_id):
        await send_verification_message(update)
        return

    # Download and send photo to enhancement API
    photo_file = await update.message.photo[-1].get_file()
    file_url = photo_file.file_path
    api_url = f"{ENHANCER_API_URL}{file_url}"
    await update.message.reply_text("Enhancing your photo, please wait...")

    try:
        response = requests.get(api_url)
        response.raise_for_status()

        data = response.json()
        if data.get("status") == "success":
            enhanced_image_url = data.get("image")
            if enhanced_image_url:
                enhanced_image_data = requests.get(enhanced_image_url)
                enhanced_image_data.raise_for_status()

                with open("enhanced_image.png", "wb") as f:
                    f.write(enhanced_image_data.content)
                with open("enhanced_image.png", "rb") as f:
                    await update.message.reply_document(document=InputFile(f), caption="Here is your enhanced image!")
            else:
                await update.message.reply_text("Error: Enhancement failed to return an image URL.")
        else:
            await update.message.reply_text("Enhancement failed. Please try again later.")

    except requests.RequestException as e:
        logger.error(f"API request error: {e}")
        await update.message.reply_text("Failed to connect to the enhancement service. Please try again later.")

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
