import logging

import mysql
from chatgpt import NextQuestion
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from utils import is_previous_message_not_answered_yet

logger = logging.getLogger(__name__)
mysql_db = mysql.MySQL()
CHAT_MODES = config.chat_modes


async def sinus_congestion_start_handler(
    update: Update, context: CallbackContext, message=None, use_new_dialog_timeout=True
) -> None:
    if await is_previous_message_not_answered_yet(update, context):
        return
    reply_text = "I see that you are suffering from <b>Sinus Congestion</b>\n<b>How long have you been suffering from this?</b>\n\n**Please start all your messages with <code>sinus:</code>\nExample: <code>sinus: I am suffering from sinus congestion since last 6 days.</code>"
    user_id = update.message.from_user.id
    mysql_db.add_sinus_congestion_record(
        user_id, "please tell me since when are you facing this issue."
    )
    await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)


async def next_sinus_question_answer_callback(
    update: Update, context: CallbackContext
) -> None:
    if await is_previous_message_not_answered_yet(update, context):
        return
    user_id = update.message.from_user.id
    mysql_db.answer_last_sinus_congestion_prompt(
        user_id, update.message.text.replace("sinus:", "").strip()
    )
    previous_qnas = mysql_db.get_sinus_congestion_qnas(user_id)
    messages = [
        {
            "role": "system",
            "content": CHAT_MODES["default"]["prompt_start"],
        },
        {"role": "user", "content": "I'm suffering from sinus congestion."},
    ]
    for previous_qna in previous_qnas:
        if previous_qna.answer and previous_qna.question:
            messages.append({"role": "assistant", "content": previous_qna.question})
            messages.append({"role": "user", "content": previous_qna.answer})
    patient_history = mysql_db.prepare_patient_history(user_id)
    messages = [
        *messages,
        *patient_history,
    ]
    next_question = (
        NextQuestion().generate_next_detailed_message_based_on_input_and_context(
            messages
        )
    )
    mysql_db.add_sinus_congestion_record(user_id, next_question)
    await update.message.reply_text(next_question, parse_mode=ParseMode.HTML)
