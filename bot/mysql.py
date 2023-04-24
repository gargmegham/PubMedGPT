import base64
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Column, DateTime, Float, Integer, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import config

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, nullable=False)
    username = Column(Text, nullable=False)
    first_name = Column(Text, default="")
    last_name = Column(Text, default="")
    last_interaction = Column(DateTime, default=datetime.utcnow)
    first_seen = Column(DateTime, default=datetime.utcnow)
    current_dialog_id = Column(Text, default="")
    current_chat_mode = Column(Text, default="default")
    current_model = Column(Text, default=config.models["available_text_models"][0])
    n_used_tokens = Column(JSON, default={})
    age = Column(Integer, default=0)
    gender = Column(Text, default="Unknown")  # M / F / O
    address = Column(Text, default="Unknown")


class Allergy(Base):
    __tablename__ = "allergies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    allergy = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class MedicalHistory(Base):
    __tablename__ = "medical_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    name = Column(Text, nullable=False)
    from_date = Column(Text, nullable=False)
    to_date = Column(Text, nullable=False)
    surgeries_performed = Column(Text, nullable=False)
    symptoms = Column(Text, nullable=False)
    medications = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Dialog(Base):
    __tablename__ = "dialogs"

    uid = Column(Text, nullable=False, primary_key=True)
    user_id = Column(Integer, nullable=False)
    chat_mode = Column(Text, default="default")
    start_time = Column(DateTime, default=datetime.utcnow)
    model = Column(Text, default=config.models["available_text_models"][0])
    messages = Column(JSON, default=[])


class QuestionAnswer(Base):
    __tablename__ = "qna"

    id = Column(Integer, primary_key=True)
    prompt = Column(Text, nullable=False)
    completion = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


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
