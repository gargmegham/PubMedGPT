import logging
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
import mysql

logger = logging.getLogger(__name__)
mysql_db = mysql.MySQL()

"""
Conversation flow:
    1. /registeration
    2. ask gender
    3. ask age
    4. ask allergies
    5. ask about medical history
    6. ask about address
    7. ask about phone number
    8. ask about email
    9. ask about bio
"""

GENDER, AGE, ALLERGIES, MEDICAL_HISTORY, LOCATION = range(5)


async def start(update: Update, context: CallbackContext) -> int:
    """Starts the conversation and asks the user about their gender."""
    reply_keyboard = [["Male", "Female", "Other"]]
    await update.message.reply_text(
        "Please specify your biological gender?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="Male, Female or Other?",
        ),
    )
    return GENDER


async def gender(update: Update, context: CallbackContext) -> int:
    """Stores the selected gender and asks for age."""
    user = update.message.from_user
    mysql_db.set_user_attribute(
        user.id,
        "gender",
        update.message.text,
    )
    await update.message.reply_text(
        "I see! Please tell me your age."
    )
    return AGE


async def age(update: Update, context: CallbackContext) -> int:
    """Stores the selected age and asks for allergies."""
    user = update.message.from_user
    mysql_db.set_user_attribute(
        user.id,
        "age",
        update.message.text,
    )
    await update.message.reply_text(
        "Please tell me about your allergies if any, or send /skip if you don't have any.\
        You can send multiple allergies just copy below format, and modify it according to your details.\n\n\
        Allergies: pollen, juniper, dust mites, mold, cats, dogs, cockroaches\
        "
    )
    return ALLERGIES


async def allergies(update: Update, context: CallbackContext) -> int:
    """
    Stores the allergies and asks for medical history.
    medical history format:
    Condition: name from_date to_date surgeries_performed symptoms medications
    """
    user = update.message.from_user
    allergies = update.message.text.split(":")[1].split(",")
    for allergy in allergies:
        mysql_db.add_new_allergy(
            user.id,
            allergy.strip(),
        )
    await update.message.reply_text(
        "Please tell me about your medical history, or send /skip if you don't have any.\n\
        You can send multiple medical conditions copy below format, and modify it according to your details.\n\n\
        Condition: diabetes from 2010-01-01 to 2015-01-01\n\
        Surgeries Performed: gastric bypass, gallbladder removal\n\
        Symptoms: fatigue, weight loss, frequent urination\n\
        Medications: metformin, insulin, lantus\n\
        "
    )
    return MEDICAL_HISTORY

async def skip_allergies(update: Update, context: CallbackContext) -> int:
    """Skips the allergies and asks for medical history."""
    await update.message.reply_text(
        "I bet you have great genes!\n\
        Now, tell me about your medical history, or send /skip if you don't have any.\n\
        You can send multiple medical conditions copy below format, and modify it according to your details.\n\n\
        Condition: diabetes\n\
        From: 2010-01-01\n\
        To: 2015-01-01\n\
        Surgeries Performed: gastric bypass, gallbladder removal\n\
        Symptoms: fatigue, weight loss, frequent urination\n\
        Medications: metformin, insulin, lantus\n\
        "
    )
    return MEDICAL_HISTORY

async def medical_history(update: Update, context: CallbackContext) -> int:
    """Stores the medical history and asks for location."""
    user = update.message.from_user
    lines = update.message.text.splitlines()
    condition = ""
    from_date = ""
    to_date = ""
    surgeries_performed = ""
    symptoms = ""
    medications = ""
    for line in lines:
        if line.startswith("Condition:"):
            condition = line.split(":")[1].strip()
        elif line.startswith("From:"):
            from_date = line.split(":")[1].strip()
        elif line.startswith("To:"):
            to_date = line.split(":")[1].strip()
        elif line.startswith("Surgeries Performed:"):
            surgeries_performed = line.split(":")[1].strip()
        elif line.startswith("Symptoms:"):
            symptoms = line.split(":")[1].strip()
        elif line.startswith("Medications:"):
            medications = line.split(":")[1].strip()
    mysql_db.add_new_medical_history(
        user.id,
        condition,
        from_date,
        to_date,
        surgeries_performed,
        symptoms,
        medications,
    )
    await update.message.reply_text(
        'I"ll take note of that. Now, send me your location please, or send /skip.'
    )
    return LOCATION

async def skip_medical_history(update: Update, context: CallbackContext) -> int:
    """Skips the medical history and asks for location."""
    await update.message.reply_text(
        'You seem a bit paranoid! Now, send me your location please, or send /skip.'
    )
    return LOCATION

async def location(update: Update, context: CallbackContext) -> int:
    """Stores the location and ends the conversation."""
    user = update.message.from_user
    user_location = update.message.location
    mysql_db.set_user_attribute(
        user.id,
        "address",
        f"{user_location.latitude}, {user_location.longitude}"
    )
    await update.message.reply_text("Thank you! I will take all of this into account while assisting you in the future.")
    return ConversationHandler.END

async def skip_location(update: Update, context: CallbackContext) -> int:
    """Skips the location and ends the conversation."""
    await update.message.reply_text("I bet you live in a nice neighborhood anyway!")
    return ConversationHandler.END

async def end(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text(
        "\
        Please make sure you have provided all the information correctly.\n\
        If you want to add any information, please use /registeration command again.\n\
        ", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def registeration_conversation_handler() -> ConversationHandler:
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("registeration", start)],
        states={
            GENDER: [MessageHandler(filters.Regex("^(Male|Female|Other)$"), gender)],
            AGE: [
                MessageHandler(filters.Regex("^(0?[1-9]|[1-9][0-9])$"), age),
            ],
            ALLERGIES: [
                MessageHandler(filters.Regex("^(Allergies: .*)$"), allergies),
                CommandHandler("skip", skip_allergies),
            ],
            MEDICAL_HISTORY: [
                MessageHandler(filters.Regex("^(Condition: .*)$"), medical_history),
                CommandHandler("skip", skip_medical_history),
            ],
            LOCATION: [
                MessageHandler(filters.LOCATION, location),
                CommandHandler('skip', skip_location),
            ],
        },
        fallbacks=[CommandHandler("end", end)],
    )
    return conv_handler
