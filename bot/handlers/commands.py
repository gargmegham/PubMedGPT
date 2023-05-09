import io
from datetime import datetime

import handlers
import medicalgpt
from handlers.message import message_handler
from mysql import MySQL
from tables import Booking, User
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from utils import is_previous_message_not_answered_yet, register_user_if_not_exists

mysql_db = MySQL()

# setup
user_tasks = {}


class CommandHandler:
    async def start_handle(update: Update, context: CallbackContext):
        if await register_user_if_not_exists(update, context, update.message.from_user):
            return
        user_id = update.message.from_user.id
        mysql_db.set_attribute(user_id, "last_interaction", datetime.now())
        mysql_db.start_new_dialog(user_id)
        reply_text = "Hi! I'm <b>Maya</b> your personal medical assistant 🤖.\nPlease click on /new to start a new conversation, or click /register if you've not registered yet."
        await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)

    async def help_handle(update: Update, context: CallbackContext):
        if await register_user_if_not_exists(update, context, update.message.from_user):
            return
        user_id = update.message.from_user.id
        mysql_db.set_attribute(user_id, "last_interaction", datetime.now())
        await update.message.reply_text(
            """Hi! I'm <b>Maya</b> your personal medical assistant 🤖.\n⚪ /register - Register yourself as a patient\n⚪ /new - Start new conversation\n⚪ /retry - Regenerate last bot answer\n⚪ /cancel - Cancel current conversation\n⚪ /help - Show this help message\n⚪ /call - Book an appointment, if not already booked""",
            parse_mode=ParseMode.HTML,
        )

    async def retry_handle(update: Update, context: CallbackContext):
        if await is_previous_message_not_answered_yet(update, context):
            return
        user_id = update.message.from_user.id
        mysql_db.set_attribute(user_id, "last_interaction", datetime.now())
        dialog_messages = mysql_db.get_dialog_messages(user_id, dialog_id=None)
        if len(dialog_messages) == 0:
            await update.message.reply_text("No message to retry 🤷‍♂️")
            return
        last_dialog_message = dialog_messages.pop()
        mysql_db.set_dialog_messages(user_id, dialog_messages, dialog_id=None)
        await message_handler(
            update,
            context,
            message=last_dialog_message["user"],
            use_new_dialog_timeout=False,
        )

    async def new_dialog_handle(update: Update, context: CallbackContext):
        if await is_previous_message_not_answered_yet(update, context):
            return
        user_id = update.message.from_user.id
        mysql_db.set_attribute(user_id, "last_interaction", datetime.now())
        mysql_db.start_new_dialog(user_id)
        await update.message.reply_text("Let's start a fresh conversation ✅")
        await update.message.reply_text(
            f"{medicalgpt.CHAT_MODES['default']['welcome_message']}",
            parse_mode=ParseMode.HTML,
        )

    async def cancel_handle(update: Update, context: CallbackContext):
        if await register_user_if_not_exists(update, context, update.message.from_user):
            return
        user_id = update.message.from_user.id
        mysql_db.set_attribute(user_id, "last_interaction", datetime.now())
        if user_id in user_tasks:
            task = user_tasks[user_id]
            task.cancel()
            return
        await update.message.reply_text(
            "<i>Nothing to cancel...</i>", parse_mode=ParseMode.HTML
        )

    async def call_handle(update: Update, context: CallbackContext):
        if await register_user_if_not_exists(update, context, update.message.from_user):
            return
        user_id = update.message.from_user.id
        mysql_db.set_attribute(user_id, "last_interaction", datetime.now())
        if mysql_db.check_if_object_exists(
            user_id,
            False,
            Booking,
        ):
            await update.message.reply_text(
                "You've already booked an appointment 📅\n\nPlease pay your dues by clicking on /pay",
                parse_mode=ParseMode.HTML,
            )
            return
        await update.message.reply_text(
            "Please use below link to book an appointment 📅\n\nhttps://cal.com/agroha-solutions/medical-gpt",
            parse_mode=ParseMode.HTML,
        )
