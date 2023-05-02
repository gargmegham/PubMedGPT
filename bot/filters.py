import medicalgpt
from telegram import Message
from telegram.ext import filters

import config


def get_user_filter():
    filter = filters.ALL
    if len(config.allowed_telegram_usernames) > 0:
        usernames = config.allowed_telegram_usernames
        user_ids = [x for x in config.allowed_telegram_usernames if isinstance(x, int)]
        # developer_telegram_username
        if config.developer_telegram_username is not None:
            usernames.append(config.developer_telegram_username)
        filter = filters.User(username=usernames) | filters.User(user_id=user_ids)
    return filter


def get_messages_that_indicate_a_certian_medical_condition(
    condition: str,
) -> filters.MessageFilter:
    """
    This is a custom filter for messages that indicate nasal congestion.
    """

    class CustomFilter(filters.MessageFilter):
        def filter(self, message: Message) -> bool:
            return medicalgpt.Filter().medical_condition_message_filter(
                message, condition
            )

    return CustomFilter()


def get_messages_that_start_with(
    text: str,
) -> filters.MessageFilter:
    """
    This is a custom filter for messages that indicate nasal congestion.
    """

    class CustomFilter(filters.MessageFilter):
        def filter(self, message: Message) -> bool:
            return message.text is not None and message.text.startswith(text)

    return CustomFilter()
