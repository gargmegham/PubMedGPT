import openai
import tiktoken
from mysql import MySQL

import config

openai.api_key = config.openai_api_key
mysql_db = MySQL()


CHAT_MODES = config.chat_modes

OPENAI_COMPLETION_OPTIONS = {
    "temperature": 0.7,
    "max_tokens": 1000,
    "top_p": 1,
    "frequency_penalty": 0,
    "presence_penalty": 0,
}


class BaseMedicalGPT:
    def _generate_prompt_messages(
        self,
        message,
        dialog_messages,
        prompt=CHAT_MODES["default"]["prompt_start"],
        user_id: int = None,
        disease_id: int = None,
    ):
        messages = [{"role": "system", "content": prompt}]
        patient_details_messages = []
        if user_id is not None:
            patient_details_messages = list(
                mysql_db.prepare_patient_history(user_id, disease_id=disease_id)
            )
        for dialog_message in dialog_messages:
            messages.append({"role": "user", "content": dialog_message["user"]})
            messages.append({"role": "assistant", "content": dialog_message["bot"]})
        messages.extend(patient_details_messages)
        messages.append({"role": "user", "content": message})
        return messages

    def _count_tokens_from_messages(self, messages, answer):
        encoding = tiktoken.encoding_for_model("gpt-4")
        # every message follows <im_start>{role/name}\n{content}<im_end>\n
        tokens_per_message = 4
        # if there's a name, the role is omitted
        tokens_per_name = -1
        # input
        n_input_tokens = 0
        for message in messages:
            n_input_tokens += tokens_per_message
            for key, value in message.items():
                n_input_tokens += len(encoding.encode(value))
                if key == "name":
                    n_input_tokens += tokens_per_name
        n_input_tokens += 2
        # output
        n_output_tokens = 1 + len(encoding.encode(answer))
        return n_input_tokens, n_output_tokens


class MedicalGPT(BaseMedicalGPT):
    async def send_message_stream(
        self, message, dialog_messages=[], user_id: int = None, disease_id: int = None
    ):
        n_dialog_messages_before = len(dialog_messages)
        answer = None
        while answer is None:
            try:
                messages = self._generate_prompt_messages(
                    message, dialog_messages, user_id=user_id, disease_id=disease_id
                )
                r_gen = await openai.ChatCompletion.acreate(
                    model="gpt-4",
                    messages=messages,
                    stream=True,
                    **OPENAI_COMPLETION_OPTIONS,
                )

                answer = ""
                async for r_item in r_gen:
                    delta = r_item.choices[0].delta
                    if "content" in delta:
                        answer += delta.content
                        (
                            n_input_tokens,
                            n_output_tokens,
                        ) = self._count_tokens_from_messages(messages, answer)
                        n_first_dialog_messages_removed = (
                            n_dialog_messages_before - len(dialog_messages)
                        )
                        yield "not_finished", answer, (
                            n_input_tokens,
                            n_output_tokens,
                        ), n_first_dialog_messages_removed
                answer = str(answer).strip()

            except openai.error.InvalidRequestError as e:  # too many tokens
                if len(dialog_messages) == 0:
                    raise e

                # forget first message in dialog_messages
                dialog_messages = dialog_messages[1:]

        yield "finished", answer, (
            n_input_tokens,
            n_output_tokens,
        ), n_first_dialog_messages_removed  # sending final answer


class Filter:
    def medical_condition_message_filter(self, message, condition) -> bool:
        """
        Given a message from the user, check if user has this medical condition
        :return: True if user has this medical condition, False otherwise
        """
        condition = condition.split("_")
        condition = " ".join(condition)
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": f"Question: is following sentence indicating {condition}?\nSentence: {message}.\nIf you're uncertain, respond with 'no'.\nAnswer: yes/no",
                },
            ],
            stream=False,
            **OPENAI_COMPLETION_OPTIONS,
        )
        response = str(response.choices[0].message.content.strip())
        if "yes" in response.lower():
            return True
        return False
