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
    n_transcribed_seconds = Column(Float, default=0.0)
    age = Column(Integer, default=0)
    gender = Column(Text, default="Unknown")  # M / F / O
    address = Column(Text, default="Unknown")
    phone_number = Column(Text, default="Unknown")
    email = Column(Text, default="Unknown")
    """
    medical_history: [{
        "name": "Diabetes",
        "from": "2019-01-01",
        "to": "2020-01-01",
        "description": "Diabetes description"
        "severity": "Mild"
        "surgeries_performed": ["Surgery 1", "Surgery 2"]
        "symptoms": ["Symptom 1", "Symptom 2"]
        "medications": ["Medication 1", "Medication 2"]
    }]
    family_history: [{
        "name": "Diabetes",
        "from": "2019-01-01",
        "to": "2020-01-01",
        "description": "Diabetes description"
        "severity": "Mild"
        "surgeries_performed": ["Surgery 1", "Surgery 2"]
        "symptoms": ["Symptom 1", "Symptom 2"]
        "medications": ["Medication 1", "Medication 2"]
    }]
    """
    medical_info = Column(
        JSON,
        default={
            "allergies": [],
            "medical_history": [],
            "family_history": [],
        },
    )


class Dialog(Base):
    __tablename__ = "dialogs"

    id = Column(Text, primary_key=True)
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

    def create_tables_if_not_exists(self):
        Base.metadata.create_all(self.engine)

    def check_if_user_exists(self, user_id: int):
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

    def start_new_dialog(self, user_id: int):
        self.check_if_user_exists(user_id, raise_exception=True)
        dialog_id = str(uuid.uuid4())
        session = self.Session()
        # add new dialog
        session.add(
            Dialog(
                id=dialog_id,
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
            .filter_by(id=dialog_id, user_id=user_id)
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
        session.query(Dialog).filter_by(id=dialog_id, user_id=user_id).update(
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
