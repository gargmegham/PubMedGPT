import openai
import tiktoken

import config

openai.api_key = config.openai_api_key


CHAT_MODES = config.chat_modes

OPENAI_COMPLETION_OPTIONS = {
    "temperature": 0.7,
    "max_tokens": 1000,
    "top_p": 1,
    "frequency_penalty": 0,
    "presence_penalty": 0,
}


class ChatGPT:
    def __init__(self):
        self.model = "gpt-3.5-turbo"

    async def send_message(self, message, dialog_messages=[]):
        n_dialog_messages_before = len(dialog_messages)
        answer = None
        while answer is None:
            try:
                messages = self._generate_prompt_messages(message, dialog_messages)
                r = await openai.ChatCompletion.acreate(
                    model=self.model, messages=messages, **OPENAI_COMPLETION_OPTIONS
                )
                answer = r.choices[0].message["content"]
                answer = self._postprocess_answer(answer)
                n_input_tokens, n_output_tokens = (
                    r.usage.prompt_tokens,
                    r.usage.completion_tokens,
                )
            except openai.error.InvalidRequestError as e:  # too many tokens
                if len(dialog_messages) == 0:
                    raise ValueError(
                        "Dialog messages is reduced to zero, but still has too many tokens to make completion"
                    ) from e

                # forget first message in dialog_messages
                dialog_messages = dialog_messages[1:]

        n_first_dialog_messages_removed = n_dialog_messages_before - len(
            dialog_messages
        )

        return (
            answer,
            (n_input_tokens, n_output_tokens),
            n_first_dialog_messages_removed,
        )

    async def send_message_stream(self, message, dialog_messages=[]):
        n_dialog_messages_before = len(dialog_messages)
        answer = None
        while answer is None:
            try:
                messages = self._generate_prompt_messages(message, dialog_messages)
                r_gen = await openai.ChatCompletion.acreate(
                    model=self.model,
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
                answer = self._postprocess_answer(answer)

            except openai.error.InvalidRequestError as e:  # too many tokens
                if len(dialog_messages) == 0:
                    raise e

                # forget first message in dialog_messages
                dialog_messages = dialog_messages[1:]

        yield "finished", answer, (
            n_input_tokens,
            n_output_tokens,
        ), n_first_dialog_messages_removed  # sending final answer

    def _generate_prompt_messages(self, message, dialog_messages):
        prompt = CHAT_MODES["default"]["prompt_start"]

        messages = [{"role": "system", "content": prompt}]
        for dialog_message in dialog_messages:
            messages.append({"role": "user", "content": dialog_message["user"]})
            messages.append({"role": "assistant", "content": dialog_message["bot"]})
        messages.append({"role": "user", "content": message})

        return messages

    def _postprocess_answer(self, answer):
        answer = answer.strip()
        return answer

    def _count_tokens_from_messages(self, messages, answer):
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

        tokens_per_message = (
            4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
        )
        tokens_per_name = -1  # if there's a name, the role is omitted

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


class BaseMedicalGPT:
    def _generate_response(
        self,
        prompt,
        max_tokens,
        n,
        temperature,
        model="gpt-3.5-turbo",
        previous_messages=[],
    ):
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an advanced medical expert chatbot assistant.\nYour primary goal is to assist users to the best of your ability with thier medical, health and psychological needs.\nYou should always ask clarifying questions before assisting the user, ask necessary information from patient specific to thier issue, and then providing helpful information, and diagnosis based on your analysis of patients details.\nIn order to effectively diagnosing users, it is important to be detailed and thorough in your responses. Use examples and evidence to support your points and justify your recommendations or solutions.\nRemember to always prioritize the needs and satisfaction of the patient.\nYour ultimate goal is to provide a helpful and enjoyable experience for the user.\nIf user asks you help related to anything which does not seem like a job of professional medical assistant, or asks to perform any task which is not relevant to medicine, health and your expertise as a medical assistant do not answer his question, but be sure to advise him to only use your service for medical needs.",
                },
                *previous_messages,
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            n=n,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()


class Filter(BaseMedicalGPT):
    def medical_condition_message_filter(self, message, condition) -> bool:
        """
        Given a message from the user, check if user has this medical condition
        :return: True if user has this medical condition, False otherwise
        """
        prompt = f"Please respond with 'yes' or 'no' based on whether the following message indicates the user has {condition}. If you're uncertain, respond with 'no'.\n\nMessage: {message}\n\nAnswer: "
        response = self._generate_response(prompt, 2, 1, 0.5)
        print(f"******{response}******")
        return self._interpret_response_as_binary(response)

    def _interpret_response_as_binary(self, response: str) -> bool:
        """
        If response contains yes,
        """
        if "yes" in response.lower() or "y" in response.lower():
            return True
        else:
            return False


class NextQuestion(BaseMedicalGPT):
    def generate_next_detailed_message_based_on_input_and_context(
        self, previous_messages
    ):
        prompt = f"""
        As a medical assistant, please provide ask a clarifying question or provide a description based on patients history, previous chat context and given system instructions.
        Clarifying Question/Prescription: 
        """
        response = self._generate_response(
            prompt, 1000, 1, 0.5, previous_messages=previous_messages
        )
        return response
