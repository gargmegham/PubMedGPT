import logging

from mysql import MySQL
from tables import Allergy, MedicalCondition, Medication, Surgery
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

mysql_db = MySQL()

logger = logging.getLogger(__name__)

(
    AGE,
    GENDER,
    IS_PREGNANT,
    OTHER_QUESTIONS,
) = range(4)

questions_meta = {
    "allergy": {
        "next_question": "medical_condition",
        "table": Allergy,
        "question": "Do you have any allergies?\nFor example: <code>Penicillin, Dust Mites</code>",
    },
    "medical_condition": {
        "next_question": "medication",
        "table": MedicalCondition,
        "question": "Do you have any medical conditions?\nFor example: <code>Asthma, Diabetes</code>",
    },
    "medication": {
        "next_question": "surgery",
        "table": Medication,
        "question": "Do you take any medications?\nFor example: <code>Paracetamol, Ibuprofen</code>",
    },
    "surgery": {
        "next_question": "end",
        "table": Surgery,
        "question": "Have you had any surgeries?\nFor example: <code>Appendectomy, Tonsillectomy</code>",
    },
}


async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        "What is your age?\nFor example: <code>20</code>",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML,
    )
    return AGE


async def age(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    if not update.message.text.isdigit():
        await update.message.reply_text(
            "Please enter a valid age.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.HTML,
        )
        return AGE
    mysql_db.set_attribute(
        user.id,
        "age",
        update.message.text,
    )
    reply_keyboard = [["Male", "Female"]]
    await update.message.reply_text(
        "Please click on your biological gender.",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
        parse_mode=ParseMode.HTML,
    )
    return GENDER


async def gender(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    gender = update.message.text
    if gender not in ["Male", "Female"]:
        reply_keyboard = [["Male", "Female"]]
        await update.message.reply_text(
            "Please enter a valid gender.",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True
            ),
            parse_mode=ParseMode.HTML,
        )
        return GENDER
    mysql_db.set_attribute(
        user.id,
        "gender",
        gender,
    )
    if gender == "Female":
        reply_keyboard = [["Yes", "No"]]
        await update.message.reply_text(
            "Are you pregnant?",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True
            ),
            parse_mode=ParseMode.HTML,
        )
        return IS_PREGNANT
    context.user_data["current_question"] = "allergy"
    await update.message.reply_text(
        f'{questions_meta["allergy"]["question"]}\nFor skipping this question, click on "/skip"',
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML,
    )
    return OTHER_QUESTIONS


async def is_pregnant(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    answer = update.message.text
    if answer not in ["Yes", "No"]:
        reply_keyboard = [["Yes", "No"]]
        await update.message.reply_text(
            "Please enter a valid answer.",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True
            ),
            parse_mode=ParseMode.HTML,
        )
        return IS_PREGNANT
    mysql_db.set_attribute(
        user.id,
        "is_pregnant",
        update.message.text == "Yes",
    )
    context.user_data["current_question"] = "allergies"
    await update.message.reply_text(
        f'{questions_meta["allergy"]["question"]}\nFor skipping this question, click on "/skip"',
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML,
    )
    return OTHER_QUESTIONS


async def other_questions(update: Update, context: CallbackContext) -> int:
    try:
        current_question = context.user_data["current_question"]
        user = update.message.from_user
        info = update.message.text
        mysql_db.add_instance(
            user.id,
            questions_meta[current_question]["table"],
            {
                "detail": info,
            },
        )
        context.user_data["current_question"] = questions_meta[current_question][
            "next_question"
        ]
        await update.message.reply_text(
            f'{questions_meta[questions_meta[current_question]["next_question"]]["question"]}\nFor skipping this question, click on "/skip"',
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.HTML,
        )
        if questions_meta[current_question]["next_question"] == "end":
            await update.message.reply_text(
                "Thanks for your information. If you want to add any information, please use /register command again.\nPlease tell me how can I help you?",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode=ParseMode.HTML,
            )
            return ConversationHandler.END
        return OTHER_QUESTIONS
    except KeyError:
        await update.message.reply_text(
            "Thanks for your information. If you want to add any information, please use /register command again.\nPlease tell me how can I help you?",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END


async def skip(update: Update, context: CallbackContext) -> int:
    try:
        current_question = context.user_data["current_question"]
        context.user_data["current_question"] = questions_meta[current_question][
            "next_question"
        ]
        await update.message.reply_text(
            f'{questions_meta[questions_meta[current_question]["next_question"]]["question"]}\nFor skipping this question, click on "/skip"',
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.HTML,
        )
        if questions_meta[current_question]["next_question"] == "end":
            await update.message.reply_text(
                "If you want to add any information, please use /register command again.\nPlease tell me how can I help you?",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode=ParseMode.HTML,
            )
            return ConversationHandler.END
        return OTHER_QUESTIONS
    except KeyError:
        await update.message.reply_text(
            "Thanks for your information. If you want to add any information, please use /register command again.\nPlease tell me how can I help you?",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END


async def end(update: Update, context: CallbackContext) -> int:
    """Ends the conversation."""
    await update.message.reply_text(
        "If you want to add any information, please use /register command again.\nPlease tell me how can I help you?",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


def registeration_handler(user_filter) -> ConversationHandler:
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("register", start)],
        states={
            AGE: [
                MessageHandler(filters.Regex("^[0-9]+(\.[0-9]+)?$") & user_filter, age)
            ],
            GENDER: [
                MessageHandler(filters.Regex("^(Male|Female)$") & user_filter, gender)
            ],
            IS_PREGNANT: [
                MessageHandler(filters.Regex("^(Yes|No)$") & user_filter, is_pregnant)
            ],
            OTHER_QUESTIONS: [
                MessageHandler(
                    filters.Regex("^(?!/skip).*$") & user_filter, other_questions
                ),
                CommandHandler("skip", skip),
            ],
        },
        fallbacks=[CommandHandler("end", end)],
    )
    return conv_handler
