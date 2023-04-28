import io
from datetime import datetime

import chatgpt
import mysql
from message import message_handler
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from utils import is_previous_message_not_answered_yet, register_user_if_not_exists

# setup
mysql_db = mysql.MySQL()
user_tasks = {}


class CommandHandler:
    async def start_handle(update: Update, context: CallbackContext):
        if await register_user_if_not_exists(update, context, update.message.from_user):
            return
        user_id = update.message.from_user.id
        mysql_db.set_user_attribute(user_id, "last_interaction", datetime.now())
        mysql_db.start_new_dialog(user_id)

        reply_text = "Hi! I'm <b>Maya</b> your personal medical assistant 🤖.\nWelcome back! Please click on /new to start a new conversation.\nIf you've not registered yet, please click on /register."
        await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)

    async def help_handle(update: Update, context: CallbackContext):
        if await register_user_if_not_exists(update, context, update.message.from_user):
            return
        user_id = update.message.from_user.id
        mysql_db.set_user_attribute(user_id, "last_interaction", datetime.now())
        await update.message.reply_text(
            """Hi! I'm <b>Maya</b> your personal medical assistant 🤖.\n⚪ /register - Register yourself as a patient\n⚪ /new - Start new conversation\n⚪ /retry - Regenerate last bot answer\n⚪ /cancel - Cancel current conversation\n⚪ /extract - Extract my prompt data from SQL database\n⚪ /help - Show this help message""",
            parse_mode=ParseMode.HTML,
        )

    async def retry_handle(update: Update, context: CallbackContext):
        if await is_previous_message_not_answered_yet(update, context):
            return

        user_id = update.message.from_user.id
        mysql_db.set_user_attribute(user_id, "last_interaction", datetime.now())

        dialog_messages = mysql_db.get_dialog_messages(user_id, dialog_id=None)
        if len(dialog_messages) == 0:
            await update.message.reply_text("No message to retry 🤷‍♂️")
            return

        last_dialog_message = dialog_messages.pop()
        mysql_db.set_dialog_messages(
            user_id, dialog_messages, dialog_id=None
        )  # last message was removed from the context

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
        mysql_db.set_user_attribute(user_id, "last_interaction", datetime.now())

        mysql_db.start_new_dialog(user_id)
        await update.message.reply_text("Starting new dialog ✅")

        chat_mode = mysql_db.get_user_attribute(user_id, "current_chat_mode")
        await update.message.reply_text(
            f"{chatgpt.CHAT_MODES[chat_mode]['welcome_message']}",
            parse_mode=ParseMode.HTML,
        )

    async def cancel_handle(update: Update, context: CallbackContext):
        await register_user_if_not_exists(update, context, update.message.from_user)
        user_id = update.message.from_user.id
        mysql_db.set_user_attribute(user_id, "last_interaction", datetime.now())
        if user_id in user_tasks:
            task = user_tasks[user_id]
            task.cancel()
        else:
            await update.message.reply_text(
                "<i>Nothing to cancel...</i>", parse_mode=ParseMode.HTML
            )

    async def extract_prompt_completion_handle(
        update: Update, context: CallbackContext
    ):
        if await is_previous_message_not_answered_yet(update, context):
            return
        user_id = update.message.from_user.id
        mysql_db.set_user_attribute(user_id, "last_interaction", datetime.now())
        response_jsonl = mysql_db.extract_qna_json()
        await update.message.reply_document(
            document=io.BytesIO(response_jsonl),
            filename="prompt_completion_data.jsonl",
            caption="Here is your data. You can use it to train your own model.",
        )
