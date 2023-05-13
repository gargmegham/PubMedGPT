import html
import json
import logging
import traceback

import telegram
from handlers.commands import CommandHandler
from handlers.disease import disease, disease_start_handler
from handlers.message import message_handler
from handlers.registeration import registeration_handler
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

import config

logger = logging.getLogger(__name__)


def split_text_into_chunks(text, chunk_size):
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]


async def error_handler(update: Update, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    try:
        # collect error message
        tb_list = traceback.format_exception(
            None, context.error, context.error.__traceback__
        )
        tb_string = "".join(tb_list)
        update_str = update.to_dict() if isinstance(update, Update) else str(update)
        message = (
            f"An exception was raised while handling an update\n"
            f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
            "</pre>\n\n"
            f"<pre>{html.escape(tb_string)}</pre>"
        )
        # split text into multiple messages due to 4096 character limit
        developer_chat_id = config.developer_telegram_chatid
        for message_chunk in split_text_into_chunks(message, 4096):
            try:
                await context.bot.send_message(
                    developer_chat_id, message_chunk, parse_mode=ParseMode.HTML
                )
                await context.bot.send_message(
                    update.effective_chat.id,
                    "🚫 An error occurred while processing your request.\nThe developer 🧑🏻‍💻 has been notified.\nPlease try again later. 🙏",
                    parse_mode=ParseMode.HTML,
                )
            except telegram.error.BadRequest:
                # answer has invalid characters, so we send it without parse_mode
                await context.bot.send_message(developer_chat_id, message_chunk)
    except Exception as error:
        await context.bot.send_message(
            developer_chat_id,
            f"⛽️ Following error in error handler 😂\n{error}\n\n{traceback.format_exc()}",
        )
