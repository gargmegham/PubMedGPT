import base64
import uuid
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tables import (
    Allergy,
    Base,
    Dialog,
    MedicalHistory,
    QuestionAnswer,
    SinusCongestionQnA,
    User,
)

import config


class MySQL:
    def __init__(self):
        self.engine = create_engine(config.mysql_uri)
        self.Session = sessionmaker(bind=self.engine)
        self.create_tables_if_not_exists()

    def create_tables_if_not_exists(self):
        Base.metadata.create_all(self.engine)

    def check_if_user_exists(self, user_id: int, raise_exception: bool = False) -> bool:
        session = self.Session()
        user = session.query(User).filter_by(id=user_id).first()
        session.close()
        return user is not None

    def add_new_user(
        self,
        user_id: int,
        chat_id: int,
        username: str = "",
        first_name: str = "",
        last_name: str = "",
    ):
        session = self.Session()
        session.add(
            User(
                id=user_id,
                chat_id=chat_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
        )
        session.commit()
        session.close()

    def get_user_attribute(self, user_id: int, attribute: str):
        session = self.Session()
        user = session.query(User).filter_by(id=user_id).first()
        session.close()
        return getattr(user, attribute)

    def set_user_attribute(self, user_id: int, attribute: str, value):
        session = self.Session()
        session.query(User).filter_by(id=user_id).update({attribute: value})
        session.commit()
        session.close()

    def add_new_allergy(self, user_id: int, allergy: str):
        self.check_if_user_exists(user_id, raise_exception=True)
        session = self.Session()
        session.add(
            Allergy(
                user_id=user_id,
                allergy=allergy,
            )
        )
        session.commit()
        session.close()

    def add_new_medical_history(
        self,
        user_id: int,
        name: str,
        from_date: str,
        to_date: str,
        surgeries_performed: str,
        symptoms: str,
        medications: str,
    ):
        self.check_if_user_exists(user_id, raise_exception=True)
        session = self.Session()
        session.add(
            MedicalHistory(
                user_id=user_id,
                name=name,
                from_date=from_date,
                to_date=to_date,
                surgeries_performed=surgeries_performed,
                symptoms=symptoms,
                medications=medications,
            )
        )
        session.commit()
        session.close()

    def start_new_dialog(self, user_id: int):
        self.check_if_user_exists(user_id, raise_exception=True)
        dialog_id = str(uuid.uuid4())
        session = self.Session()
        # add new dialog
        session.add(
            Dialog(
                uid=dialog_id,
                user_id=user_id,
                chat_mode=self.get_user_attribute(user_id, "current_chat_mode"),
                model=self.get_user_attribute(user_id, "current_model"),
            )
        )
        # update user's current dialog
        session.query(User).filter_by(id=user_id).update(
            {"current_dialog_id": dialog_id}
        )
        session.commit()
        session.close()
        return dialog_id

    def update_n_used_tokens(
        self, user_id: int, model: str, n_input_tokens: int, n_output_tokens: int
    ):
        n_used_tokens_dict = self.get_user_attribute(user_id, "n_used_tokens")
        if model in n_used_tokens_dict:
            n_used_tokens_dict[model]["n_input_tokens"] += n_input_tokens
            n_used_tokens_dict[model]["n_output_tokens"] += n_output_tokens
        else:
            n_used_tokens_dict[model] = {
                "n_input_tokens": n_input_tokens,
                "n_output_tokens": n_output_tokens,
            }
        self.set_user_attribute(user_id, "n_used_tokens", n_used_tokens_dict)

    def get_dialog_messages(self, user_id: int, dialog_id: Optional[str] = None):
        self.check_if_user_exists(user_id, raise_exception=True)
        if dialog_id is None:
            dialog_id = self.get_user_attribute(user_id, "current_dialog_id")
        session = self.Session()
        dialog_messages = (
            session.query(Dialog)
            .filter_by(uid=dialog_id, user_id=user_id)
            .first()
            .messages
        )
        return dialog_messages

    def set_dialog_messages(
        self, user_id: int, dialog_messages: list, dialog_id: Optional[str] = None
    ):
        self.check_if_user_exists(user_id, raise_exception=True)
        if dialog_id is None:
            dialog_id = self.get_user_attribute(user_id, "current_dialog_id")
        session = self.Session()
        session.query(Dialog).filter_by(uid=dialog_id, user_id=user_id).update(
            {"messages": dialog_messages}
        )
        session.commit()
        session.close()

    def insert_qna(self, prompt: str, completion: str):
        base64_prompt = base64.b64encode(prompt.encode("utf-8")).decode("utf-8")
        base64_completion = base64.b64encode(completion.encode("utf-8")).decode("utf-8")
        session = self.Session()
        session.add(QuestionAnswer(prompt=base64_prompt, completion=base64_completion))
        session.commit()

    def extract_qna_json(self):
        session = self.Session()
        entries = session.query(QuestionAnswer).all()
        session.close()
        jsonl_response = ""
        for entry in entries:
            jsonl_response += f'{{"prompt": "{base64.b64decode(str(entry.prompt)).decode("utf-8")}", "completion": "{base64.b64decode(str(entry.completion)).decode("utf-8")}"}}\n'
        return jsonl_response.encode("utf-8")

    def add_sinus_congestion_record(self, user_id: int, question: str):
        self.check_if_user_exists(user_id, raise_exception=True)
        session = self.Session()
        session.add(SinusCongestionQnA(user_id=user_id, question=question))
        session.commit()
        session.close()

    def answer_last_sinus_congestion_prompt(self, user_id: int, answer: str):
        self.check_if_user_exists(user_id, raise_exception=True)
        session = self.Session()
        # find last prompt by timestamp and update its answer
        last_prompt = (
            session.query(SinusCongestionQnA)
            .filter_by(user_id=user_id)
            .order_by(SinusCongestionQnA.timestamp.desc())
            .first()
        )
        session.query(SinusCongestionQnA).filter_by(id=last_prompt.id).update(
            {
                "answer": answer.strip(),
            }
        )
        session.commit()
        session.close()

    def prepare_patient_history(self, user_id: int) -> str:
        """
        Prepare patient history for the doctor.
        Format should be like following:
        Patient history:
        Name: \n
        Age: \n
        Gender: \n
        Medical History: \n
            - Name: \n, From: \n, To: \n, Surgeries Performed: \n, Symptoms: \n, Medications: \n
        Allergies: \n
        """
        self.check_if_user_exists(user_id, raise_exception=True)
        session = self.Session()
        user = session.query(User).filter_by(id=user_id).first()
        history = []
        history.append(
            {
                "role": "user",
                "content": f"My name is {user.first_name} {user.last_name}",
            }
        )
        history.append({"role": "user", "content": f"My age is {user.age}"})
        history.append({"role": "user", "content": f"My gender is {user.gender}"})
        allergies = session.query(Allergy).filter_by(user_id=user_id).all()
        medical_history = session.query(MedicalHistory).filter_by(user_id=user_id).all()
        session.close()
        allergy_details = ", ".join([allergy.allergy for allergy in allergies])
        history.append(
            {"role": "user", "content": f"I'm allergic to: {allergy_details}"}
        )
        for index, med_history in enumerate(medical_history):
            history_details = ""
            if med_history.name:
                history_details = f"Name: {med_history.name}"
            if med_history.from_date:
                history_details += f", From: {med_history.from_date}"
            if med_history.to_date:
                history_details += f", To: {med_history.to_date}"
            if med_history.surgeries_performed:
                history_details += f", Surgeries Performed: {med_history.surgeries_performed}"
            if med_history.symptoms:
                history_details += f", Symptoms: {med_history.symptoms}"
            if med_history.medications:
                history_details += f", Medications: {med_history.medications}"
            if history_details:
                history.append(
                    {
                        "role": "user",
                        "content": f"Medical history - {index+1}: {history_details}",
                    }
                )
        return history

    def get_sinus_congestion_qnas(self, user_id: int) -> str:
        self.check_if_user_exists(user_id, raise_exception=True)
        session = self.Session()
        # where answers are not null and answers are not empty
        questions_and_answers = (
            session.query(SinusCongestionQnA)
            .filter(SinusCongestionQnA.answer != "")
            .filter_by(user_id=user_id)
            .all()
        )
        session.close()
        return questions_and_answers
