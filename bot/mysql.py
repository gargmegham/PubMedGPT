import uuid
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tables import Allergy, Base, Dialog, User

import config


class MySQL:
    def __init__(self):
        self.engine = create_engine(config.mysql_uri)
        self.Session = sessionmaker(bind=self.engine)
        self.create_tables_if_not_exists()

    def create_tables_if_not_exists(self):
        Base.metadata.create_all(self.engine)

    def check_if_object_exists(
        self, user_id: int, raise_exception: bool = False, model: Base = User
    ) -> bool:
        session = self.Session()
        user = session.query(model).filter_by(user_id=str(user_id)).first()
        session.close()
        if raise_exception and user is None:
            raise Exception(f"User {user_id} does not exist in the database")
        return user is not None

    def update_n_used_tokens(
        self, user_id: int, model: str, n_input_tokens: int, n_output_tokens: int
    ):
        # common function for updating n_used_tokens
        n_used_tokens_dict = self.get_attribute(user_id, "n_used_tokens")
        if model in n_used_tokens_dict:
            n_used_tokens_dict[model]["n_input_tokens"] += n_input_tokens
            n_used_tokens_dict[model]["n_output_tokens"] += n_output_tokens
        else:
            n_used_tokens_dict[model] = {
                "n_input_tokens": n_input_tokens,
                "n_output_tokens": n_output_tokens,
            }
        self.set_attribute(user_id, "n_used_tokens", n_used_tokens_dict, User)

    def start_new_dialog(self, user_id: int):
        dialog_id = str(uuid.uuid4())
        self.add_instance(
            user_id,
            Dialog,
            {
                "uid": dialog_id,
                "chat_mode": self.get_attribute(user_id, "current_chat_mode"),
                "model": self.get_attribute(user_id, "current_model"),
            },
        )
        self.set_attribute(user_id, "current_dialog_id", dialog_id, User)
        return dialog_id

    def get_dialog_messages(self, user_id: int, dialog_id: Optional[str] = None):
        if dialog_id is None:
            dialog_id = self.get_attribute(user_id, "current_dialog_id")
        return self.get_attribute(
            user_id, "messages", model=Dialog, extra_filters={"uid": dialog_id}
        )

    def set_dialog_messages(
        self, user_id: int, dialog_messages: list, dialog_id: Optional[str] = None
    ):
        if dialog_id is None:
            dialog_id = self.get_attribute(user_id, "current_dialog_id")
        self.set_attribute(
            user_id,
            "messages",
            dialog_messages,
            model=Dialog,
            extra_filters={"uid": dialog_id},
        )

    def get_attribute(
        self, user_id: int, attribute: str, model: Base = User, extra_filters: dict = {}
    ):
        session = self.Session()
        instance = (
            session.query(model)
            .filter_by(user_id=str(user_id), **extra_filters)
            .first()
        )
        session.close()
        return getattr(instance, attribute)

    def set_attribute(
        self,
        user_id: int,
        attribute: str,
        value,
        model: Base = User,
        extra_filters: dict = {},
    ):
        session = self.Session()
        session.query(model).filter_by(user_id=str(user_id), **extra_filters).update(
            {attribute: value}
        )
        session.commit()
        session.close()

    def get_instances(
        self,
        user_id: int,
        model: Base,
        find_first: bool = False,
        extra_filters: dict = None,
        id_greater_than: int = None,
    ):
        """
        Supported tables:
        """
        session = self.Session()
        instances = session.query(model)
        if user_id is not None:
            instances = instances.filter_by(user_id=str(user_id))
        if extra_filters is not None:
            instances = instances.filter_by(**extra_filters)
        if id_greater_than is not None:
            instances = instances.filter(model.id > id_greater_than)
        if find_first:
            instances = instances.order_by(model.id).first()
        else:
            instances = instances.all()
        session.close()
        return instances

    def add_instance(self, user_id: int, model: Base, data: dict):
        session = self.Session()
        instance = session.add(model(user_id=str(user_id), **data))
        session.commit()
        session.close()
        return instance

    def prepare_patient_history(self, user_id: int) -> list:
        session = self.Session()
        user = session.query(User).filter_by(user_id=str(user_id)).first()
        history = []
        history.append(
            {
                "role": "assistant",
                "content": "What's your name?",
            }
        )
        history.append(
            {
                "role": "user",
                "content": f"My name is {user.first_name} {user.last_name}",
            }
        )
        history.append(
            {
                "role": "assistant",
                "content": "What's your age?",
            }
        )
        history.append({"role": "user", "content": f"My age is {user.age}"})
        history.append(
            {
                "role": "assistant",
                "content": "What's your gender?",
            }
        )
        history.append({"role": "user", "content": f"My gender is {user.gender}"})
        allergies = session.query(Allergy).filter_by(user_id=user_id).all()
        session.close()
        allergy_details = ", ".join([allergy.allergy for allergy in allergies])
        if allergy_details:
            history.append(
                {
                    "role": "assistant",
                    "content": "Do you have any allergies?",
                }
            )
            history.append(
                {"role": "user", "content": f"I'm allergic to: {allergy_details}"}
            )
        return history
