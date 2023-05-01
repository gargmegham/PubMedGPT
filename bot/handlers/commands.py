import io
from datetime import datetime

import handlers
import medicalgpt
import mysql
from handlers.message import message_handler
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
        await update.message.reply_text(
            f"{medicalgpt.CHAT_MODES['default']['welcome_message']}",
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

    async def sinus(update: Update, context: CallbackContext):
        if await register_user_if_not_exists(update, context, update.message.from_user):
            return
        user_id = update.message.from_user.id
        mysql_db.start_new_dialog(user_id)
        user = mysql_db.get_user(user_id)
        age = user.age if user.age != "Unknown" else None
        gender = user.gender if user.gender != "Unknown" else None
        allergies = mysql_db.get_allergies(user_id)
        medical_history = mysql_db.get_medical_history(user_id)
        sinus_details = mysql_db.get_sinus_data(user_id)
        # case - 1
        if (
            int(age) > 18
            and gender == "Male"
            and len(allergies) == 0
            and len(medical_history) == 0
            and not sinus_details["otc_medications"]
        ):
            await update.message.reply_text(
                """
                You can try <b>Augmentin, Prednisone, Flonase & Mucinex</b> for sinus pain relief.\n
                Augmentin is an antibiotic that is commonly used to treat bacterial infections, including sinus infections. It is important to note that antibiotics should only be used when they are necessary, and only under the guidance of a healthcare professional.\n
                Prednisone is a corticosteroid that is often used to reduce inflammation and swelling in the body. It is commonly prescribed for a variety of conditions, including asthma, allergies, and arthritis. However, prednisone can have several side effects, including increased blood pressure, weight gain, and mood changes. It should only be used under the guidance of a healthcare professional.\n
                Flonase is a nasal spray that contains a corticosteroid called fluticasone propionate. It is used to treat nasal congestion, sneezing, and other symptoms associated with allergies or other nasal conditions. Flonase works by reducing inflammation in the nasal passages and is generally safe for long-term use.\n
                Mucinex is a medication that contains guaifenesin, which is an expectorant that helps to thin and loosen mucus in the lungs, making it easier to cough up. It is commonly used to treat cough and congestion associated with colds, flu, and other respiratory infections.\n
                It is important to note that these medications should only be used under the guidance of a healthcare professional. If you are experiencing symptoms of a sinus infection or any other medical condition, you should seek medical attention promptly. To book an appointment with a doctor, please click on /booking.
                """,
                parse_mode=ParseMode.HTML,
            )
        # unhandled case
        message = ""
        message += "Here is my sinus details:\n"
        if sinus_details.otc_medications:
            message += f"Here are some otc medications i tried: {sinus_details.otc_medications}\n"
        if sinus_details.duration:
            message += f"Duration of my sinus: {sinus_details.duration}\n"
        if sinus_details.symptoms:
            message += f"My symptoms are: {sinus_details.symptoms}\n"
        if sinus_details.fever:
            message += f"My fever details: {sinus_details.fever}\n"
        if user.gender == "Female" and sinus_details.pregnant == 1:
            message += f"I am pregnant.\n"
        message += "Please prescribe me some medicine for sinus congestion relief.\n"
        handlers.message_handler(
            update,
            context,
            message=message,
            use_new_dialog_timeout=False,
            pass_dialog_messages=False,
        )
