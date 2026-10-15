import asyncio
import logging
import os
import re
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, ChatJoinRequestHandler

# Flask web server to satisfy Render port binding
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Bot configuration and constants
TOKEN = os.environ.get('TOKEN')
CHANNELS = ['@shivam46838', '@primordiyalgood', '@killerking89', 'https://t.me/+bT3NJ4mTOksyZjk1']
ADMINS = [8682275801]

# In-memory storage for generated link payloads: { payload_id: {"chat_id": int, "start_id": int, "end_id": int} }
LINK_STORE = {}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def parse_telegram_link(link: str):
    """
    Extracts chat_id (or username) and message_id from public or private Telegram message links.
    """
    private_pattern = r"https://t\.me/c/(\d+)/(\d+)"
    public_pattern = r"https://t\.me/([\w_]+)/(\d+)"

    priv_match = re.match(private_pattern, link)
    if priv_match:
        raw_id, msg_id = priv_match.groups()
        chat_id = int(f"-100{raw_id}")
        return chat_id, int(msg_id)

    pub_match = re.match(public_pattern, link)
    if pub_match:
        username, msg_id = pub_match.groups()
        return f"@{username}", int(msg_id)

    return None, None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    payload = args[0] if args else None

    welcome_text = f"Welcome {user.first_name}! Please join all the required channels below to access your content."
    callback_data = f"check_sub_{payload}" if payload else "check_sub_none"

    keyboard = [
        [
            InlineKeyboardButton("Join Channel 1", url=f"https://t.me/{CHANNELS[0][1:]}"),
            InlineKeyboardButton("Join Channel 2", url=f"https://t.me/{CHANNELS[1][1:]}")
        ],
        [
            InlineKeyboardButton("Join Channel 3", url=f"https://t.me/{CHANNELS[2][1:]}"),
            InlineKeyboardButton("Join Channel 4", url=CHANNELS[3])
        ],
        [InlineKeyboardButton("Try Again", callback_data=callback_data)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def create_batch_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /batch <start_message_link> <end_message_link>")
        return

    start_link = context.args[0]
    end_link = context.args[1]

    start_chat, start_msg_id = parse_telegram_link(start_link)
    end_chat, end_msg_id = parse_telegram_link(end_link)

    if not start_chat or not end_chat or start_chat != end_chat:
        await update.message.reply_text("Invalid links. Both links must belong to the same channel.")
        return

    if start_msg_id > end_msg_id:
        start_msg_id, end_msg_id = end_msg_id, start_msg_id

    payload_id = f"ep_{start_msg_id}_{end_msg_id}"
    LINK_STORE[payload_id] = {
        "chat_id": start_chat,
        "start_id": start_msg_id,
        "end_id": end_msg_id
    }

    bot_username = (await context.bot.get_me()).username
    unique_link = f"https://t.me/{bot_username}?start={payload_id}"

    response = (
        f"✅ **Unique Link Generated Successfully!**\n\n"
        f"**Channel:** `{start_chat}`\n"
        f"**Range:** Message `{start_msg_id}` to `{end_msg_id}`\n\n"
        f"**Link:** {unique_link}"
    )
    await update.message.reply_text(response, parse_mode="Markdown")

async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logging.error(f"Error deleting message {message_id}: {e}")

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    all_joined = True

    for channel in CHANNELS:
        try:
            if channel.startswith("https://"):
                continue
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']:
                all_joined = False
                break
        except Exception as e:
            logging.error(f"Error checking {channel}: {e}")
            all_joined = False
            break

    payload = query.data.replace("check_sub_", "")

    if all_joined:
        await query.edit_message_text(text="Thank you! You have joined all channels. Sending your content now...")

        if payload != "none" and payload in LINK_STORE:
            data = LINK_STORE[payload]
            source_chat_id = data["chat_id"]
            start_id = data["start_id"]
            end_id = data["end_id"]

            for msg_id in range(start_id, end_id + 1):
                try:
                    sent_msg = await context.bot.copy_message(
                        chat_id=user_id,
                        from_chat_id=source_chat_id,
                        message_id=msg_id,
                        protect_content=True
                    )
                    asyncio.create_task(delete_message_after_delay(context, user_id, sent_msg.message_id, 600))
                except Exception as e:
                    logging.error(f"Error copying message {msg_id}: {e}")
                    await context.bot.send_message(chat_id=user_id, text=f"Message {msg_id} could not be retrieved.")

        footer_text = (
            "Thank you for connecting with Shivam Story Bot!\n"
            "If you want more stories, message @killer9703"
        )
        await context.bot.send_message(chat_id=user_id, text=footer_text)
    else:
        keyboard = [
            [InlineKeyboardButton("Try Again", callback_data=f"check_sub_{payload}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="You have not joined all channels yet. Please join them and click Try Again.", reply_markup=reply_markup)

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    if not context.args:
        await update.message.reply_text("Please provide a user ID to add as admin.")
        return
    try:
        new_admin_id = int(context.args[0])
        if new_admin_id not in ADMINS:
            ADMINS.append(new_admin_id)
            await update.message.reply_text(f"User {new_admin_id} added as admin.")
        else:
            await update.message.reply_text("User is already an admin.")
    except ValueError:
        await update.message.reply_text("Please provide a valid numeric user ID.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("For assistance, contact the admin: @killer9703")

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.chat_join_request
    logging.info(f"Join request received from: {request.from_user.username}")

if __name__ == '__main__':
    # Start web server thread for Render port binding
    t = Thread(target=run_web_server)
    t.start()

    if not TOKEN or TOKEN == 'YOUR_BOT_TOKEN':
        print("Error: TOKEN environment variable not found or not set properly.")
        exit(1)

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('batch', create_batch_link))
    application.add_handler(CommandHandler('addadmin', add_admin))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CallbackQueryHandler(check_subscription, pattern='^check_sub_'))
    application.add_handler(ChatJoinRequestHandler(handle_join_request))

    application.run_polling()
        
