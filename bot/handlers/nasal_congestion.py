import logging

import mysql
from chatgpt import NextQuestion
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from utils import is_previous_message_not_answered_yet

logger = logging.getLogger(__name__)

mysql_db = mysql.MySQL()


async def sinus_congestion_start_handler(
    update: Update, context: CallbackContext, message=None, use_new_dialog_timeout=True
) -> None:
    if await is_previous_message_not_answered_yet(update, context):
        return
    reply_text = "I see that you are suffering from <b>Sinus Congestion</b>\n<b>How long have you been suffering from this?</b>\n\n**Please start all your messages with <code>sinus-<code>\nExample: <code>sinus-I am suffering from sinus congestion since last 6 days.</code>"
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
        user_id, update.message.text.split("sinus-")[1].strip()
    )
    previous_qnas = mysql_db.get_sinus_congestion_qnas(user_id)
    messages = [
        {
            "role": "system",
            "content": """Here are some general guidelines for treating sinus congestion:\n\nDuration of symptoms:\nIf symptoms have persisted for more than 7 days, antibiotics might be considered.\nIf symptoms are long-standing, consider using Claritin, Pepcid, or consulting an ENT specialist.\n\nFever:\nIf you have a fever above 102.4°F for 3 days, antibiotics might be prescribed.\n\nOther symptoms:\nFor additional symptoms, refer to the relevant protocols, such as treatment for earaches, sore throats, or coughs.\nAntihistamines or nasal sprays:\n\nIf you haven't tried these yet, consider using over-the-counter options like steroids, phenylephrine, pseudoephedrine, Mucinex, Flonase, Claritin, Zyrtec, Xyzal, or Allegra.\n\nAge:\nUnder 18: Amoxicillin or Augmentin may be prescribed.\nOver 18: Adult dosages of Amoxicillin or Augmentin may be prescribed.\n\nPenicillin allergy:\nFor those with a penicillin allergy, alternatives like Cefdinir, Clindamycin, Doxycycline, or Levofloxacin may be considered.\n\nMedication interactions:\nCheck for any possible interactions with current medications before prescribing new ones.\n\nMedical problems:\nAvoid prednisone in patients with elevated blood pressure, diabetes, or gastritis.\nAvoid albuterol in patients with tachycardia or atrial fibrillation.\n\nPregnancy:\nIf pregnant, consider the following treatment options: saline mist, cromolyn, Flonase, Claritin, Augmentin, or clotrimazole cream for 7 days.\n\nKeep in mind that these are general guidelines, and it is always important to consult with a healthcare professional before starting any new treatment.""",
        },
        {"role": "user", "content": "I'm suffering from sinus congestion."},
    ]
    for previous_qna in previous_qnas:
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
