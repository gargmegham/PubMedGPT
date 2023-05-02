import logging

from mysql import MySQL
from tables import DiseaseAnswer, DiseaseQuestion
from telegram import ReplyKeyboardRemove, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from utils import is_previous_message_not_answered_yet

mysql_db = MySQL()

logger = logging.getLogger(__name__)

OTHER_QUESTIONS = range(1)


async def disease_start_handler(
    update: Update, context: CallbackContext, message=None, use_new_dialog_timeout=True
) -> None:
    if await is_previous_message_not_answered_yet(update, context):
        return
    diagnosed_with = mysql_db.get_attribute(
        update.message.from_user.id, "diagnosed_with"
    )
    diagnosed_with = diagnosed_with.split(",")[0]
    reply_text = f"I see that you are suffering from <b>{diagnosed_with}</b>\nPlease click on /disease to start the diagnosis process."
    await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)


async def start(update: Update, context: CallbackContext) -> int:
    diagnosed_with = mysql_db.get_attribute(
        update.message.from_user.id, "diagnosed_with"
    )
    diagnosed_with_id = int(diagnosed_with.split(",")[1])
    first_question = mysql_db.get_instances(
        None,
        DiseaseQuestion,
        find_first=True,
        extra_filters={"disease_id": diagnosed_with_id},
    )
    context.user_data["current_question_id"] = first_question.id
    context.user_data["diagnosed_with_id"] = diagnosed_with_id
    await update.message.reply_text(
        first_question.detail,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML,
    )
    return OTHER_QUESTIONS


async def other_questions(update: Update, context: CallbackContext) -> int:
    current_question_id = context.user_data["current_question_id"]
    diagnosed_with_id = context.user_data["diagnosed_with_id"]
    user = update.message.from_user
    info = update.message.text
    mysql_db.add_instance(
        user.id,
        DiseaseAnswer,
        {
            "detail": info,
            "disease_id": int(diagnosed_with_id),
        },
    )
    next_question = mysql_db.get_instances(
        None,
        DiseaseQuestion,
        find_first=True,
        id_greater_than=current_question_id,
        extra_filters={"disease_id": diagnosed_with_id},
    )
    if next_question is not None:
        context.user_data["current_question_id"] = next_question.id
        await update.message.reply_text(
            next_question.detail,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.HTML,
        )
        return OTHER_QUESTIONS
    await update.message.reply_text(
        "Thanks for all the information. here is your diagnosis:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML,
    )
    # TODO: get diagnosis
    return ConversationHandler.END


async def end(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text(
        "I hope this conversation was useful. Please use /booking to book an appointment.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


def disease(user_filter) -> ConversationHandler:
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("diagnose", start)],
        states={
            OTHER_QUESTIONS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & user_filter, other_questions
                ),
            ],
        },
        fallbacks=[CommandHandler("cancel", end)],
    )
    return conv_handler
