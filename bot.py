import os
import requests
from telegram import Update, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Set up your bot token here
TELEGRAM_BOT_TOKEN = os.getenv("7065470365:AAH84EEwdlbq2PtGN3xazmFjtjG_KxyHlPY")

# Enhance API endpoint
ENHANCER_API_URL = "https://olivine-tricolor-samba.glitch.me/api/enhancer?url="

# Function to handle the /start command
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Hello! Please send me a photo, and I will enhance it for you.")

# Function to handle photos
def handle_photo(update: Update, context: CallbackContext) -> None:
    photo_file = update.message.photo[-1].get_file()  # Get highest resolution photo
    file_url = photo_file.file_path  # This is the file URL on Telegram's server

    # Requesting the enhanced image from the external API
    api_url = f"{ENHANCER_API_URL}{file_url}"
    update.message.reply_text("Enhancing your photo, please wait...")

    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "success":
            enhanced_image_url = data["image"]

            # Send enhanced image link and download for the user
            update.message.reply_text(f"Here is the enhanced image link: {enhanced_image_url}")
            enhanced_image_data = requests.get(enhanced_image_url)

            if enhanced_image_data.status_code == 200:
                # Upload enhanced image directly to user
                with open("enhanced_image.png", "wb") as f:
                    f.write(enhanced_image_data.content)

                with open("enhanced_image.png", "rb") as f:
                    update.message.reply_photo(photo=InputFile(f), caption="Here is your enhanced image!")
        else:
            update.message.reply_text("Sorry, something went wrong with the enhancement.")
    else:
        update.message.reply_text("Failed to connect to the image enhancer API.")

# Main function to start the bot
def main() -> None:
    updater = Updater(TELEGRAM_BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.photo, handle_photo))

    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
