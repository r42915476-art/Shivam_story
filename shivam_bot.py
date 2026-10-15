import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, ChatJoinRequestHandler

TOKEN = '8959889439:AAHxAe15LrlsC2NIyi9HjOMN6ylgVzstkBg'
CHANNELS = ['@shivam46838', '@primordiyalgood', '@killerking89', 'https://t.me/+bT3NJ4mTOksyZjk1']
SOURCE_CHANNEL_ID = 'YOUR_SOURCE_CHANNEL_ID'

# बॉट एडमिन की आईडी
ADMINS = [8682275801]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    episode_range = "1-50"
    if args:
        episode_range = args[0]
    
    welcome_text = f"Welcome {user.first_name}! Please join all the channels below to access episodes {episode_range}."
    keyboard = [
        [
            InlineKeyboardButton("Join Channel 1", url=f"https://t.me/{CHANNELS[0][1:]}"),
            InlineKeyboardButton("Join Channel 2", url=f"https://t.me/{CHANNELS[1][1:]}")
        ],
        [
            InlineKeyboardButton("Join Channel 3", url=f"https://t.me/{CHANNELS[2][1:]}"),
            InlineKeyboardButton("Join Channel 4", url=CHANNELS[3])
        ],
        [InlineKeyboardButton("Try Again", callback_data=f'check_sub_{episode_range}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("Please provide a user ID to add as admin.")
        return
    
    try:
        new_admin_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid numeric user ID.")
        return

    if new_admin_id not in ADMINS:
        ADMINS.append(new_admin_id)
        await update.message.reply_text(f"User {new_admin_id} added as admin.")
    else:
        await update.message.reply_text("User is already an admin.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("For assistance, contact the admin: @killer9703")

async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    
    if update.message.reply_to_message:
        await context.bot.pin_chat_message(chat_id=update.effective_chat.id, message_id=update.message.reply_to_message.message_id)
        await update.message.reply_text("Message pinned.")
    else:
        await update.message.reply_text("Please reply to a message to pin it.")

async def post_to_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    await update.message.reply_text("Posting feature is ready to be implemented with specific broadcast logic.")

async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Error deleting message {message_id}: {e}")

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.chat_join_request
    print(f"Join request received from: {request.from_user.username}")

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
            print(f"Error checking {channel}: {e}")
            all_joined = False
            break

    episode_range = query.data.split('_')[2]

    if all_joined:
        await query.edit_message_text(text="Thank you! You have joined all channels. Sending your stories now...")
        
        start_ep, end_ep = map(int, episode_range.split('-'))
        for message_id in range(start_ep, end_ep + 1):
            try:
                sent_message = await context.bot.copy_message(chat_id=user_id, from_chat_id=SOURCE_CHANNEL_ID, message_id=message_id, protect_content=True)
                asyncio.create_task(delete_message_after_delay(context, user_id, sent_message.message_id, 600))
            except Exception as e:
                print(f"Error copying message {message_id}: {e}")
                await context.bot.send_message(chat_id=user_id, text=f"Episode {message_id} not found.")

        footer_text = (
            "Thank you with connecting Shivam Story Bot\n"
            "If you want more stories, message @killer9703"
        )
        await context.bot.send_message(chat_id=user_id, text=footer_text)
    else:
        keyboard = [
            [InlineKeyboardButton("Try Again", callback_data=f'check_sub_{episode_range}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="You have not joined all channels yet. Please join them and click Try Again.", reply_markup=reply_markup)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('addadmin', add_admin))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('pin', pin_message))
    application.add_handler(CommandHandler('post', post_to_users))
    application.add_handler(CallbackQueryHandler(check_subscription, pattern='check_sub_'))
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    
    application.run_polling()
