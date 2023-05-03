import asyncio
import logging

from handlers.message import message_handle_fn
from medicalgpt import MedicalGPT
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

from bot import user_semaphores, user_tasks

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
    user_id = user.id
    info = update.message.text
    mysql_db.add_instance(
        user_id,
        DiseaseAnswer,
        {
            "detail": info,
            "disease_id": int(diagnosed_with_id),
            "question_id": int(current_question_id),
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
    async with user_semaphores[user_id]:
        task = asyncio.create_task(
            message_handle_fn(
                update=update,
                context=context,
                message="Based on the given information, provide the best possible advice for me as a patient.",
                use_new_dialog_timeout=True,
                pass_dialog_messages=False,
                user_id=user_id,
                disease_id=int(diagnosed_with_id),
            )
        )
        user_tasks[user_id] = task
        try:
            await task
        except asyncio.CancelledError:
            await update.message.reply_text("✅ Canceled", parse_mode=ParseMode.HTML)
        else:
            pass
        finally:
            mysql_db.set_attribute(user_id, "diagnosed_with", "")
            update.message.reply_text(
                "✅ Please use /booking to book an appointment with our recommended doctor.",
                parse_mode=ParseMode.HTML,
            )
            if user_id in user_tasks:
                del user_tasks[user_id]
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
        entry_points=[CommandHandler("disease", start)],
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
