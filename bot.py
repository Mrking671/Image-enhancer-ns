import os
import requests
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, CallbackContext, CallbackQueryHandler
)
import aiohttp

# Bot Token and API URLs
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ENHANCER_API_URL = "https://olivine-tricolor-samba.glitch.me/api/enhancer?url="
KOYEB_DATABASE_URL = ""
REQUIRED_CHANNEL = "@yourchannel"
LOG_CHANNEL = "@yourlogchannel"
ADMINS = ["@youradminusername", "youradminid"]

# Helper function to check channel subscription
async def is_user_subscribed(user_id):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChatMember?chat_id={REQUIRED_CHANNEL}&user_id={user_id}") as resp:
            data = await resp.json()
            return data["result"]["status"] in ("member", "administrator", "creator")

# Function to log successful verification
async def log_verification(user_id):
    await app.bot.send_message(chat_id=LOG_CHANNEL, text=f"User {user_id} has verified successfully.")

# Start command with subscription check
async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    if await is_user_subscribed(user.id):
        await update.message.reply_text("Hello! Please send me a photo, and I will enhance it for you.")
        await log_verification(user.id)
    else:
        keyboard = [[InlineKeyboardButton("Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")]]
        await update.message.reply_text("Please join the channel first to use this bot.", reply_markup=InlineKeyboardMarkup(keyboard))

# Handle photo uploads
async def handle_photo(update: Update, context: CallbackContext) -> None:
    if not await is_user_subscribed(update.effective_user.id):
        await start(update, context)
        return

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
            
            enhanced_image_data = requests.get(enhanced_image_url)
            if enhanced_image_data.status_code == 200:
                with open("enhanced_image.png", "wb") as f:
                    f.write(enhanced_image_data.content)

                with open("enhanced_image.png", "rb") as f:
                    await update.message.reply_photo(photo=InputFile(f), caption="Here is your enhanced image!")
        else:
            await update.message.reply_text("Sorry, something went wrong with the enhancement.")
    else:
        await update.message.reply_text("Failed to connect to the image enhancer API.")

# Broadcast command for admins
async def broadcast(update: Update, context: CallbackContext):
    if str(update.effective_user.id) not in ADMINS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    message = " ".join(context.args)
    if not message:
        await update.message.reply_text("Please provide a message to broadcast.")
        return

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{KOYEB_DATABASE_URL}/users") as response:
            users = await response.json()

    for user in users:
        try:
            await app.bot.send_message(chat_id=user['id'], text=message)
        except Exception as e:
            print(f"Failed to send message to {user['id']}: {e}")

    await update.message.reply_text("Broadcast message sent.")

# User count command for admins
async def user_count(update: Update, context: CallbackContext):
    if str(update.effective_user.id) not in ADMINS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{KOYEB_DATABASE_URL}/users") as response:
            users = await response.json()
    
    await update.message.reply_text(f"Total users: {len(users)}")

# Main function to start the bot with webhook
async def main():
    global app
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("usercount", user_count))

    await app.start()
    await app.updater.start_webhook(listen="0.0.0.0", port=int(os.environ.get("PORT", "8443")), url_path=TELEGRAM_BOT_TOKEN)
    await app.bot.set_webhook(f"https://your-domain.com/{TELEGRAM_BOT_TOKEN}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
