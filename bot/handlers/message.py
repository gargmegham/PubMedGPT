import asyncio
import logging
import traceback
from datetime import datetime

import medicalgpt
import telegram
from mysql import MySQL
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from utils import edited_message_handle, is_previous_message_not_answered_yet

import config
from bot import user_semaphores, user_tasks

# setup
mysql_db = MySQL()
logger = logging.getLogger(__name__)


async def message_handle_fn(
    update,
    context,
    message,
    use_new_dialog_timeout,
    pass_dialog_messages,
    user_id,
    disease_id: int = None,
):
    # new dialog timeout
    if use_new_dialog_timeout:
        if (
            datetime.now() - mysql_db.get_attribute(user_id, "last_interaction")
        ).seconds > config.new_dialog_timeout and len(
            mysql_db.get_dialog_messages(user_id)
        ) > 0:
            mysql_db.start_new_dialog(user_id)
            await update.message.reply_text(
                f"Starting new dialog due to timeout (<b>{medicalgpt.CHAT_MODES['default']['name']}</b> mode) ✅",
                parse_mode=ParseMode.HTML,
            )
    mysql_db.set_attribute(user_id, "last_interaction", datetime.now())
    # in case of CancelledError
    n_input_tokens, n_output_tokens = 0, 0
    current_model = mysql_db.get_attribute(user_id, "current_model")
    try:
        # send placeholder message to user
        placeholder_message = await update.message.reply_text("typing...")
        # send typing action
        await update.message.chat.send_action(action="typing")
        _message = message or update.message.text
        dialog_messages = (
            mysql_db.get_dialog_messages(user_id, dialog_id=None)
            if pass_dialog_messages
            else []
        )
        parse_mode = {"html": ParseMode.HTML, "markdown": ParseMode.MARKDOWN}[
            medicalgpt.CHAT_MODES["default"]["parse_mode"]
        ]
        gpt_instance = medicalgpt.MedicalGPT()
        gen = gpt_instance.send_message_stream(
            _message,
            dialog_messages=dialog_messages,
            user_id=user_id,
            disease_id=disease_id,
        )
        prev_answer = ""
        async for gen_item in gen:
            (
                status,
                answer,
                (n_input_tokens, n_output_tokens),
                n_first_dialog_messages_removed,
            ) = gen_item
            answer = answer[:4096]  # telegram message limit
            # update only when 100 new symbols are ready
            if abs(len(answer) - len(prev_answer)) < 100 and status != "finished":
                continue
            try:
                await context.bot.edit_message_text(
                    answer,
                    chat_id=placeholder_message.chat_id,
                    message_id=placeholder_message.message_id,
                    parse_mode=parse_mode,
                )
            except telegram.error.BadRequest as e:
                if str(e).startswith("Message is not modified"):
                    continue
                else:
                    await context.bot.edit_message_text(
                        answer,
                        chat_id=placeholder_message.chat_id,
                        message_id=placeholder_message.message_id,
                    )
            await asyncio.sleep(0.01)  # wait a bit to avoid flooding
            prev_answer = answer
        # update user data
        new_dialog_message = {
            "user": _message,
            "bot": answer,
        }
        mysql_db.set_dialog_messages(
            user_id,
            mysql_db.get_dialog_messages(user_id, dialog_id=None)
            + [new_dialog_message],
            dialog_id=None,
        )
        mysql_db.update_n_used_tokens(
            user_id, current_model, n_input_tokens, n_output_tokens
        )
    except asyncio.CancelledError:
        mysql_db.update_n_used_tokens(
            user_id, current_model, n_input_tokens, n_output_tokens
        )
        raise

    except Exception as e:
        error_text = f"Something went wrong during completion. Reason: {e}\n\nTraceback: {traceback.format_exc()}"
        logger.error(error_text)
        await update.message.reply_text(error_text)
        return

    # send message if some messages were removed from the context
    if n_first_dialog_messages_removed > 0:
        if n_first_dialog_messages_removed == 1:
            text = "✍️ <i>Note:</i> Your current dialog is too long, so your <b>first message</b> was removed from the context.\n Send /new command to start new dialog"
        else:
            text = f"✍️ <i>Note:</i> Your current dialog is too long, so <b>{n_first_dialog_messages_removed} first messages</b> were removed from the context.\n Send /new command to start new dialog"
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def message_handler(
    update: Update,
    context: CallbackContext,
    message=None,
    use_new_dialog_timeout=True,
    pass_dialog_messages=True,
):
    # check if message is edited
    if update.edited_message is not None:
        await edited_message_handle(update, context)
        return
    if await is_previous_message_not_answered_yet(update, context):
        return
    user_id = update.message.from_user.id
    if user_id not in user_semaphores:
        user_semaphores[user_id] = asyncio.Semaphore(1)
    async with user_semaphores[user_id]:
        task = asyncio.create_task(
            message_handle_fn(
                update=update,
                context=context,
                message=message,
                use_new_dialog_timeout=use_new_dialog_timeout,
                pass_dialog_messages=pass_dialog_messages,
                user_id=user_id,
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
            if user_id in user_tasks:
                del user_tasks[user_id]
