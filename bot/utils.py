import asyncio
import logging

import mysql
from telegram import Update, User
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from utils import register_user_if_not_exists

import config

# setup
mysql_db = mysql.MySQL()
logger = logging.getLogger(__name__)
user_semaphores = {}
user_tasks = {}


async def register_user_if_not_exists(
    update: Update, context: CallbackContext, user: User
):
    if not mysql_db.check_if_user_exists(user.id):
        mysql_db.add_new_user(
            user.id,
            update.message.chat_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
        mysql_db.start_new_dialog(user.id)

    if mysql_db.get_user_attribute(user.id, "current_dialog_id") is None:
        mysql_db.start_new_dialog(user.id)

    if user.id not in user_semaphores:
        user_semaphores[user.id] = asyncio.Semaphore(1)

    if mysql_db.get_user_attribute(user.id, "current_model") is None:
        mysql_db.set_user_attribute(
            user.id, "current_model", config.models["available_text_models"][0]
        )

    # back compatibility for n_used_tokens field
    n_used_tokens = mysql_db.get_user_attribute(user.id, "n_used_tokens")
    if isinstance(n_used_tokens, int):  # old format
        new_n_used_tokens = {
            "gpt-3.5-turbo": {"n_input_tokens": 0, "n_output_tokens": n_used_tokens}
        }
        mysql_db.set_user_attribute(user.id, "n_used_tokens", new_n_used_tokens)


async def is_previous_message_not_answered_yet(
    update: Update, context: CallbackContext
):
    await register_user_if_not_exists(update, context, update.message.from_user)

    user_id = update.message.from_user.id
    if user_semaphores[user_id].locked():
        text = "⏳ Please <b>wait</b> for a reply to the previous message\n"
        text += "Or you can /cancel it"
        await update.message.reply_text(
            text, reply_to_message_id=update.message.id, parse_mode=ParseMode.HTML
        )
        return True
    else:
        return False


async def edited_message_handle(update: Update, context: CallbackContext):
    text = "🥲 Unfortunately, message <b>editing</b> is not supported"
    await update.edited_message.reply_text(text, parse_mode=ParseMode.HTML)
