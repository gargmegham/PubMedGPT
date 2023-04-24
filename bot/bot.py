import asyncio
import html
import io
import json
import logging
import traceback
from datetime import datetime

import mysql
import openai_utils
import telegram
from registeration import registeration_conversation_handler
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    User,
)
from telegram.constants import ParseMode
from telegram.ext import (
    AIORateLimiter,
    Application,
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

import config

# setup
mysql_db = mysql.MySQL()
logger = logging.getLogger(__name__)
user_semaphores = {}
user_tasks = {}

HELP_MESSAGE = """Commands:
⚪ /retry - Regenerate last bot answer
⚪ /new - Start new conversation
⚪ /mode - Select chat mode
⚪ /model - Select GPT model
⚪ /balance - Show balance
⚪ /extract - Extract my prompt data from SQL database
⚪ /help - Show help
"""


def split_text_into_chunks(text, chunk_size):
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]


async def register_user_if_not_exists(
    update: Update, context: CallbackContext, user: User
):
    if not mysql_db.check_if_user_exists(user.id):
        mysql_db.add_new_user(
            user.id,
            update.message.chat_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
        mysql_db.start_new_dialog(user.id)

    if mysql_db.get_user_attribute(user.id, "current_dialog_id") is None:
        mysql_db.start_new_dialog(user.id)

    if user.id not in user_semaphores:
        user_semaphores[user.id] = asyncio.Semaphore(1)

    if mysql_db.get_user_attribute(user.id, "current_model") is None:
        mysql_db.set_user_attribute(
            user.id, "current_model", config.models["available_text_models"][0]
        )

    # back compatibility for n_used_tokens field
    n_used_tokens = mysql_db.get_user_attribute(user.id, "n_used_tokens")
    if isinstance(n_used_tokens, int):  # old format
        new_n_used_tokens = {
            "gpt-3.5-turbo": {"n_input_tokens": 0, "n_output_tokens": n_used_tokens}
        }
        mysql_db.set_user_attribute(user.id, "n_used_tokens", new_n_used_tokens)


async def start_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.message.from_user.id
    mysql_db.set_user_attribute(user_id, "last_interaction", datetime.now())
    mysql_db.start_new_dialog(user_id)
    reply_text = "Hi! I'm <b>Maya</b> your medical assistant, an implementation of GPT-3.5 OpenAI API language model🤖"
    if not mysql_db.check_if_user_exists(update.message.from_user.id):
        reply_text += "\nLet's start with your registeration as a patient, please click on /registeration."
    else:
        reply_text += "\nLet's continue our conversation, you can use enter / to see command list.\nIf you're not registered as a patient, please click on /registeration."
    await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)


async def help_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.message.from_user.id
    mysql_db.set_user_attribute(user_id, "last_interaction", datetime.now())
    await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.HTML)


async def retry_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
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

    await message_handle(
        update,
        context,
        message=last_dialog_message["user"],
        use_new_dialog_timeout=False,
    )


async def message_handle(
    update: Update, context: CallbackContext, message=None, use_new_dialog_timeout=True
):
    # check if message is edited
    if update.edited_message is not None:
        await edited_message_handle(update, context)
        return
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await is_previous_message_not_answered_yet(update, context):
        return
    user_id = update.message.from_user.id

    async def message_handle_fn():
        chat_mode = mysql_db.get_user_attribute(user_id, "current_chat_mode")
        # new dialog timeout
        if use_new_dialog_timeout:
            if (
                datetime.now()
                - mysql_db.get_user_attribute(user_id, "last_interaction")
            ).seconds > config.new_dialog_timeout and len(
                mysql_db.get_dialog_messages(user_id)
            ) > 0:
                mysql_db.start_new_dialog(user_id)
                await update.message.reply_text(
                    f"Starting new dialog due to timeout (<b>{openai_utils.CHAT_MODES[chat_mode]['name']}</b> mode) ✅",
                    parse_mode=ParseMode.HTML,
                )
        mysql_db.set_user_attribute(user_id, "last_interaction", datetime.now())
        # in case of CancelledError
        n_input_tokens, n_output_tokens = 0, 0
        current_model = mysql_db.get_user_attribute(user_id, "current_model")
        try:
            # send placeholder message to user
            placeholder_message = await update.message.reply_text(
                "*****Please Wait*****"
            )
            # send typing action
            await update.message.chat.send_action(action="typing")
            _message = message or update.message.text
            dialog_messages = mysql_db.get_dialog_messages(user_id, dialog_id=None)
            parse_mode = {"html": ParseMode.HTML, "markdown": ParseMode.MARKDOWN}[
                openai_utils.CHAT_MODES[chat_mode]["parse_mode"]
            ]
            chatgpt_instance = openai_utils.ChatGPT(model=current_model)
            if config.enable_message_streaming:
                gen = chatgpt_instance.send_message_stream(
                    _message, dialog_messages=dialog_messages, chat_mode=chat_mode
                )
            else:
                (
                    answer,
                    (n_input_tokens, n_output_tokens),
                    n_first_dialog_messages_removed,
                ) = await chatgpt_instance.send_message(
                    _message, dialog_messages=dialog_messages, chat_mode=chat_mode
                )

                async def fake_gen():
                    yield "finished", answer, (
                        n_input_tokens,
                        n_output_tokens,
                    ), n_first_dialog_messages_removed

                gen = fake_gen()
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

            # create table in sql db if not exists
            mysql_db.insert_qna(prompt=_message, completion=answer)

        except asyncio.CancelledError:
            # note: intermediate token updates only work when enable_message_streaming=True (config.yml)
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

    async with user_semaphores[user_id]:
        task = asyncio.create_task(message_handle_fn())
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


async def is_previous_message_not_answered_yet(
    update: Update, context: CallbackContext
):
    await register_user_if_not_exists(update, context, update.message.from_user)

    user_id = update.message.from_user.id
    if user_semaphores[user_id].locked():
        text = "⏳ Please <b>wait</b> for a reply to the previous message\n"
        text += "Or you can /cancel it"
        await update.message.reply_text(
            text, reply_to_message_id=update.message.id, parse_mode=ParseMode.HTML
        )
        return True
    else:
        return False


async def new_dialog_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await is_previous_message_not_answered_yet(update, context):
        return

    user_id = update.message.from_user.id
    mysql_db.set_user_attribute(user_id, "last_interaction", datetime.now())

    mysql_db.start_new_dialog(user_id)
    await update.message.reply_text("Starting new dialog ✅")

    chat_mode = mysql_db.get_user_attribute(user_id, "current_chat_mode")
    await update.message.reply_text(
        f"{openai_utils.CHAT_MODES[chat_mode]['welcome_message']}",
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


def get_settings_menu(user_id: int):
    current_model = mysql_db.get_user_attribute(user_id, "current_model")
    text = config.models["info"][current_model]["description"]

    text += "\n\n"
    score_dict = config.models["info"][current_model]["scores"]
    for score_key, score_value in score_dict.items():
        text += "🟢" * score_value + "⚪️" * (5 - score_value) + f" - {score_key}\n\n"

    text += "\nSelect <b>model</b>:"

    # buttons to choose models
    buttons = []
    for model_key in config.models["available_text_models"]:
        title = config.models["info"][model_key]["name"]
        if model_key == current_model:
            title = "✅ " + title

        buttons.append(
            InlineKeyboardButton(title, callback_data=f"set_settings|{model_key}")
        )
    reply_markup = InlineKeyboardMarkup([buttons])

    return text, reply_markup


async def model_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await is_previous_message_not_answered_yet(update, context):
        return

    user_id = update.message.from_user.id
    mysql_db.set_user_attribute(user_id, "last_interaction", datetime.now())

    text, reply_markup = get_settings_menu(user_id)
    await update.message.reply_text(
        text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
    )


async def set_settings_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(
        update.callback_query, context, update.callback_query.from_user
    )
    user_id = update.callback_query.from_user.id

    query = update.callback_query
    await query.answer()

    _, model_key = query.data.split("|")
    mysql_db.set_user_attribute(user_id, "current_model", model_key)
    mysql_db.start_new_dialog(user_id)

    text, reply_markup = get_settings_menu(user_id)
    try:
        await query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )
    except telegram.error.BadRequest as e:
        if str(e).startswith("Message is not modified"):
            pass


async def extract_prompt_completion_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
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


async def show_balance_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)

    user_id = update.message.from_user.id
    mysql_db.set_user_attribute(user_id, "last_interaction", datetime.now())

    # count total usage statistics
    total_n_spent_dollars = 0
    total_n_used_tokens = 0

    n_used_tokens_dict = mysql_db.get_user_attribute(user_id, "n_used_tokens")

    details_text = "🏷️ Details:\n"
    for model_key in sorted(n_used_tokens_dict.keys()):
        n_input_tokens, n_output_tokens = (
            n_used_tokens_dict[model_key]["n_input_tokens"],
            n_used_tokens_dict[model_key]["n_output_tokens"],
        )
        total_n_used_tokens += n_input_tokens + n_output_tokens

        n_input_spent_dollars = config.models["info"][model_key][
            "price_per_1000_input_tokens"
        ] * (n_input_tokens / 1000)
        n_output_spent_dollars = config.models["info"][model_key][
            "price_per_1000_output_tokens"
        ] * (n_output_tokens / 1000)
        total_n_spent_dollars += n_input_spent_dollars + n_output_spent_dollars

        details_text += f"- {model_key}: <b>{n_input_spent_dollars + n_output_spent_dollars:.03f}$</b> / <b>{n_input_tokens + n_output_tokens} tokens</b>\n"

    text = f"You spent <b>{total_n_spent_dollars:.03f}$</b>\n"
    text += f"You used <b>{total_n_used_tokens}</b> tokens\n\n"
    text += details_text

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def edited_message_handle(update: Update, context: CallbackContext):
    text = "🥲 Unfortunately, message <b>editing</b> is not supported"
    await update.edited_message.reply_text(text, parse_mode=ParseMode.HTML)


async def error_handle(update: Update, context: CallbackContext) -> None:
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
        for message_chunk in split_text_into_chunks(message, 4096):
            try:
                await context.bot.send_message(
                    update.effective_chat.id, message_chunk, parse_mode=ParseMode.HTML
                )
            except telegram.error.BadRequest:
                # answer has invalid characters, so we send it without parse_mode
                await context.bot.send_message(update.effective_chat.id, message_chunk)
    except:
        await context.bot.send_message(
            update.effective_chat.id, "Some error in error handler"
        )


async def post_init(application: Application):
    """
    ⚪ /retry - Regenerate last bot answer
    ⚪ /new - Start new conversation
    ⚪ /mode - Select chat mode
    ⚪ /model - Select GPT model
    ⚪ /balance - Show balance
    ⚪ /sql - Extract my prompt data from SQL database
    ⚪ /help - Show available commands
    """
    await application.bot.set_my_commands(
        [
            BotCommand(command="/new", description="Start new conversation"),
            BotCommand(command="/mode", description="Select chat mode"),
            BotCommand(command="/retry", description="Regenerate last bot answer"),
            BotCommand(command="/balance", description="Show balance"),
            BotCommand(command="/model", description="Select GPT model"),
            BotCommand(command="/help", description="Show available commands"),
            BotCommand(
                command="/extract",
                description="Extract my prompt data from SQL database",
            ),
        ]
    )


def run_bot() -> None:
    application = (
        ApplicationBuilder()
        .token(config.telegram_token)
        .concurrent_updates(True)
        .rate_limiter(AIORateLimiter(max_retries=5))
        .post_init(post_init)
        .build()
    )
    # filter for allowed users
    user_filter = filters.ALL
    if len(config.allowed_telegram_usernames) > 0:
        usernames = config.allowed_telegram_usernames
        user_ids = [x for x in config.allowed_telegram_usernames if isinstance(x, int)]
        # developer_telegram_username
        if config.developer_telegram_username is not None:
            usernames.append(config.developer_telegram_username)
        user_filter = filters.User(username=usernames) | filters.User(user_id=user_ids)
    # add handlers
    application.add_handler(CommandHandler("start", start_handle, filters=user_filter))
    application.add_handler(CommandHandler("help", help_handle, filters=user_filter))
    application.add_handler(CommandHandler("retry", retry_handle, filters=user_filter))
    application.add_handler(
        CommandHandler("new", new_dialog_handle, filters=user_filter)
    )
    application.add_handler(
        CommandHandler("cancel", cancel_handle, filters=user_filter)
    )
    application.add_handler(
        CommandHandler("extract", extract_prompt_completion_handle, filters=user_filter)
    )
    application.add_handler(CommandHandler("model", model_handle, filters=user_filter))
    application.add_handler(
        CommandHandler("balance", show_balance_handle, filters=user_filter)
    )
    application.add_handler(
        CallbackQueryHandler(set_settings_handle, pattern="^set_settings")
    )
    #  add conversation handlers
    application.add_handler(registeration_conversation_handler(user_filter))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & user_filter, message_handle)
    )
    # add error handler
    application.add_error_handler(error_handle)
    # start the bot
    application.run_polling()


if __name__ == "__main__":
    run_bot()
