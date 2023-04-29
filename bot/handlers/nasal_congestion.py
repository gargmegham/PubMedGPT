import logging

import mysql
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from utils import is_previous_message_not_answered_yet

logger = logging.getLogger(__name__)
mysql_db = mysql.MySQL()
DURATION, FEVER, SYMPTOMS, OTC_MEDICATIONS, PREGNANT_OR_BREASTFEEDING = range(5)


async def sinus_congestion_start_handler(
    update: Update, context: CallbackContext, message=None, use_new_dialog_timeout=True
) -> None:
    if await is_previous_message_not_answered_yet(update, context):
        return
    reply_text = "I see that you are suffering from <b>Sinus Congestion</b>\nPlease click on /sinus to start related conversation."
    user_id = update.message.from_user.id
    mysql_db.add_sinus_congestion_record(user_id)
    await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)


async def start(update: Update, context: CallbackContext) -> int:
    """Starts the conversation and asks the user about the duration of sinus."""
    reply_keyboard = [
        [
            "It's been more than a week",
            "It's been less than a week",
            "It's been more than a month",
        ]
    ]
    await update.message.reply_text(
        "Please specify the duration of your sinus?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
        ),
    )
    return DURATION


async def duration(update: Update, context: CallbackContext) -> int:
    """Stores the selected duration and asks for fever."""
    duration = update.message.text
    if duration:
        user = update.message.from_user
        mysql_db.update_sinus_congestion_attribute(
            user.id,
            "duration",
            duration,
        )
    reply_keyboard = [
        [
            "It's more 102.4°F",
            "It's less than 102.4°F",
            "I don't have fever",
        ]
    ]
    await update.message.reply_text(
        "Do you have fever?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
        ),
    )
    return FEVER


async def fever(update: Update, context: CallbackContext) -> int:
    """
    Stores the selected fever and asks for symptoms.
    """
    fever = update.message.text
    if fever:
        user = update.message.from_user
        mysql_db.update_sinus_congestion_attribute(
            user.id,
            "fever",
            fever,
        )
    await update.message.reply_text(
        "Please tell me about your symptoms if any, or send /skip if you don't have any.\n\You can send multiple symptoms just copy below format, and modify it according to your details.\n\n<code>Symptoms: headache, facial pain, nasal congestion, runny nose, postnasal drip, sore throat, cough, fever, bad breath, fatigue, dental pain, ear pain, pain in the jaw and cheeks, swelling around the eyes, nose, and cheeks</code>",
        parse_mode=ParseMode.HTML,
    )
    return SYMPTOMS


async def skip_sympotms(update: Update, context: CallbackContext) -> int:
    """
    Stores the selected fever and asks for symptoms.
    """
    await update.message.reply_text(
        "Please tell me if you are taking any OTC medications, or send /skip if you don't have any.\n\You can send multiple OTC medications just copy below format, and modify it according to your details.\n\n<code>OTC Medications: acetaminophen, ibuprofen, naproxen, aspirin, decongestants, antihistamines, nasal sprays, nasal irrigation, saline nasal spray, nasal corticosteroids, oral corticosteroids, antibiotics, allergy shots, surgery</code>",
        parse_mode=ParseMode.HTML,
    )
    return OTC_MEDICATIONS


async def symptoms(update: Update, context: CallbackContext) -> int:
    """
    Stores the selected symptoms and asks for OTC medications.
    """
    symptoms = update.message.text.replace("Symptoms:", "")
    if symptoms:
        user = update.message.from_user
        mysql_db.update_sinus_congestion_attribute(
            user.id,
            "symptoms",
            symptoms,
        )
    await update.message.reply_text(
        "Please tell me if you are taking any OTC medications, or send /skip if you don't have any.\n\You can send multiple OTC medications just copy below format, and modify it according to your details.\n\n<code>OTC: acetaminophen, ibuprofen, naproxen, aspirin, decongestants, antihistamines, nasal sprays, nasal irrigation, saline nasal spray, nasal corticosteroids, oral corticosteroids, antibiotics, allergy shots, surgery</code>",
        parse_mode=ParseMode.HTML,
    )
    return OTC_MEDICATIONS


async def skip_otc_medications(update: Update, context: CallbackContext) -> int:
    """
    Stores the selected fever and asks for symptoms.
    """
    # check if user is female
    gender = mysql_db.get_user_attribute(
        update.message.from_user.id,
        "gender",
    )
    if gender == "Female":
        await update.message.reply_text(
            "Are you pregnant or breastfeeding?",
            reply_markup=ReplyKeyboardMarkup(
                [["Yes", "No"]],
                one_time_keyboard=True,
            ),
        )
        return PREGNANT_OR_BREASTFEEDING
    else:
        await update.message.reply_text(
            "Please click on /diagnosis to get your diagnosis.",
        )
        return ConversationHandler.END


async def otc_medications(update: Update, context: CallbackContext) -> int:
    """
    Stores the selected OTC medications and asks for pregnancy or breastfeeding.
    """
    otc_medications_ans = update.message.text.replace("OTC:", "")
    if otc_medications_ans:
        user = update.message.from_user
        mysql_db.update_sinus_congestion_attribute(
            user.id,
            "otc_medications",
            otc_medications_ans,
        )
    # check if user is female
    gender = mysql_db.get_user_attribute(
        update.message.from_user.id,
        "gender",
    )
    if gender == "Female":
        await update.message.reply_text(
            "Are you pregnant or breastfeeding?",
            reply_markup=ReplyKeyboardMarkup(
                [["Yes", "No"]],
                one_time_keyboard=True,
            ),
        )
        return PREGNANT_OR_BREASTFEEDING
    else:
        await update.message.reply_text(
            "Please click on /sinus_diagnosis to get your diagnosis.",
        )
        return ConversationHandler.END


async def pregnant_or_breastfeeding(update: Update, context: CallbackContext) -> int:
    """
    Stores the selected pregnancy or breastfeeding and asks for age.
    """
    pregnant = update.message.text.replace("Pregnant:", "")
    if pregnant:
        user = update.message.from_user
        mysql_db.update_sinus_congestion_attribute(
            user.id,
            "pregnant",
            pregnant_or_breastfeeding == "Yes",
        )
    await update.message.reply_text(
        "Please click on /sinus_diagnosis to get your diagnosis.",
    )
    return ConversationHandler.END


async def end(update: Update, context: CallbackContext) -> int:
    """
    End Conversation by command.
    """
    await update.message.reply_text(
        "Please click on /sinus_diagnosis to get your diagnosis.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


def sinus_congestion_handler(user_filter) -> ConversationHandler:
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("sinus", start)],
        states={
            DURATION: [
                MessageHandler(
                    filters.Regex(
                        "^(It's been more than a week|It's been less than a week|It's been more than a month)$"
                    )
                    & user_filter,
                    duration,
                ),
            ],
            FEVER: [
                MessageHandler(
                    filters.Regex(
                        "^(It's more 102.4°F|It's less than 102.4°F|I don't have fever)$"
                    )
                    & user_filter,
                    fever,
                ),
            ],
            SYMPTOMS: [
                MessageHandler(
                    filters.Regex("^(Symptoms: .*)$") & user_filter, symptoms
                ),
                CommandHandler("skip", skip_sympotms),
            ],
            OTC_MEDICATIONS: [
                MessageHandler(
                    filters.Regex("^(OTC: .*)$") & user_filter, otc_medications
                ),
                CommandHandler("skip", skip_otc_medications),
            ],
            PREGNANT_OR_BREASTFEEDING: [
                MessageHandler(
                    filters.Regex("^(Yes|No)$") & user_filter, pregnant_or_breastfeeding
                )
            ],
        },
        fallbacks=[CommandHandler("end", end)],
    )
    return conv_handler
