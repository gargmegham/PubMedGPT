import handlers
import mysql
from filters import get_user_filter
from tables import Disease
from telegram import BotCommand
from telegram.ext import (
    AIORateLimiter,
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

import config

user_semaphores = {}
user_tasks = {}
mysql_db = mysql.MySQL()


async def post_init(application: Application):
    diseases = mysql_db.get_instances(
        None,
        Disease,
        find_first=False,
    )
    await application.bot.set_my_commands(
        [
            BotCommand(command="/new", description="Start new conversation"),
            BotCommand(command="/retry", description="Regenerate last bot answer"),
            BotCommand(command="/help", description="Show available commands"),
            BotCommand(command="/cancel", description="Cancel current conversation"),
            BotCommand(command="/start", description="Start the bot"),
            BotCommand(
                command="/register", description="Register yourself as a patient"
            ),
            BotCommand(
                command="/skip", description="Skip the current question and move on"
            ),
        ]
        + [
            BotCommand(command=disease.detail, description=disease.detail)
            for disease in diseases
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
    user_filter = get_user_filter()
    command_handler = handlers.CommandHandler
    application.add_handler(
        CommandHandler("start", command_handler.start_handle, filters=user_filter)
    )
    application.add_handler(
        CommandHandler("help", command_handler.help_handle, filters=user_filter)
    )
    application.add_handler(
        CommandHandler("retry", command_handler.retry_handle, filters=user_filter)
    )
    application.add_handler(
        CommandHandler("new", command_handler.new_dialog_handle, filters=user_filter)
    )
    application.add_handler(
        CommandHandler("cancel", command_handler.cancel_handle, filters=user_filter)
    )
    #  add conversation handlers
    application.add_handler(handlers.registeration_handler(user_filter))
    diseases = mysql_db.get_instances(
        None,
        Disease,
        find_first=False,
    )
    for disease in diseases:
        application.add_handler(
            CommandHandler(
                disease.detail,
                handlers.disease_handler,
                filters=user_filter,
            )
        )
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & user_filter, handlers.message_handler
        )
    )
    # add error handler
    application.add_error_handler(handlers.error_handler)
    # start the bot
    application.run_polling()


if __name__ == "__main__":
    try:
        run_bot()
    except KeyboardInterrupt:
        print("Exiting...")
