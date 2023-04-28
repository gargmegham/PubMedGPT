import chatgpt
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


def get_messages_that_starts_with_and_have_atleast_n_lines(
    text: str, num_lines: int
) -> filters.BaseFilter:
    """
    This is a custom filter for multiline messages that starts with a given text.
    """

    class CustomFilter(filters.BaseFilter):
        def filter(self, message: filters.Message) -> bool:
            if message.text is None:
                return False
            if not message.text.startswith(text):
                return False
            if len(message.text.splitlines()) < num_lines:
                return False
            return True

    return CustomFilter()


def get_messages_that_indicate_a_certian_medical_condition(
    condition: str,
) -> filters.MessageFilter:
    """
    This is a custom filter for messages that indicate nasal congestion.
    """

    class CustomFilter(filters.MessageFilter):
        def filter(self, message: Message) -> bool:
            return chatgpt.Filter().medical_condition_message_filter(message, condition)

    return CustomFilter()
