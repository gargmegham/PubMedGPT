import uuid
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tables import (
    Allergy,
    Base,
    Dialog,
    DiseaseAnswer,
    DiseaseInstructions,
    DiseaseQuestion,
    MedicalCondition,
    Medication,
    Medicine,
    Surgery,
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
        find_last: bool = False,
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
        elif find_last:
            instances = instances.order_by(model.id.desc()).first()
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

    def prepare_patient_history(self, user_id: int, disease_id: int = None) -> list:
        user = self.get_instances(user_id, User, find_first=True)
        history = []
        if disease_id:
            disease_specific_instructions = "\n".join(
                [
                    instruction.detail
                    for instruction in self.get_instances(
                        None,
                        DiseaseInstructions,
                        extra_filters={"disease_id": disease_id},
                    )
                ]
            )
            history.extend(
                [
                    {
                        "role": "system",
                        "content": f"Here are some instructions for you from the doctor:\n\n{disease_specific_instructions}",
                    },
                ]
            )
        history.extend(
            [
                {
                    "role": "assistant",
                    "content": "Please tell me your name?",
                },
                {
                    "role": "user",
                    "content": f"My name is {user.first_name} {user.last_name}",
                },
                {
                    "role": "assistant",
                    "content": "What's your age?",
                },
                {"role": "user", "content": f"My age is {user.age}"},
                {
                    "role": "assistant",
                    "content": "What's your gender?",
                },
                {"role": "user", "content": f"My gender is {user.gender}"},
            ]
        )
        if user.gender == "Female":
            history.extend(
                [
                    {
                        "role": "assistant",
                        "content": "Are you pregnant?",
                    },
                    {
                        "role": "user",
                        "content": "Yes" if user.is_pregnant else "No",
                    },
                ]
            )
        allergies = "\n".join(
            [allergy.detail for allergy in self.get_instances(user_id, Allergy)]
        )
        medical_conditions = "\n".join(
            [mc.detail for mc in self.get_instances(user_id, MedicalCondition)]
        )
        medications = "\n".join(
            [
                medication.detail
                for medication in self.get_instances(user_id, Medication)
            ]
        )
        surgeries = "\n".join(
            [surgery.detail for surgery in self.get_instances(user_id, Surgery)]
        )
        history.extend(
            [
                {
                    "role": "assistant",
                    "content": "Do you have any allergies? If yes, please tell me about them.",
                },
                {
                    "role": "user",
                    "content": allergies if len(allergies) > 0 else "No",
                },
                {
                    "role": "assistant",
                    "content": "Do you have any medical conditions? If yes, please tell me about them.",
                },
                {
                    "role": "user",
                    "content": medical_conditions
                    if len(medical_conditions) > 0
                    else "No",
                },
                {
                    "role": "assistant",
                    "content": "Do you take any medications? If yes, please tell me about them.",
                },
                {
                    "role": "user",
                    "content": medications if len(medications) > 0 else "No",
                },
                {
                    "role": "assistant",
                    "content": "Have you had any surgeries? If yes, please tell me about them.",
                },
                {
                    "role": "user",
                    "content": surgeries if len(surgeries) > 0 else "No",
                },
            ]
        )
        if disease_id is not None:
            disease_specific_questions = self.get_instances(
                None, DiseaseQuestion, extra_filters={"disease_id": disease_id}
            )
            for disease_specific_question in disease_specific_questions:
                answer = self.get_instances(
                    user_id,
                    DiseaseAnswer,
                    extra_filters={"question_id": disease_specific_question.id},
                    find_last=True,
                )
                if answer is not None:
                    history.extend(
                        [
                            {
                                "role": "assistant",
                                "content": disease_specific_question.detail,
                            },
                            {
                                "role": "user",
                                "content": answer.detail,
                            },
                        ]
                    )
        return history

    def get_allowed_medicines(self, user_id: int, disease_id: int = None) -> list:
        def any_word_in_x_match_any_word_in_y(x: list, y: str):
            list1 = []
            list2 = y.split(",").map(lambda x: str(x).lower().strip())
            for sentence in x:
                list1.extend(
                    str(sentence).split(" ").map(lambda x: str(x).lower().strip())
                )
            for word in list1:
                if word in list2:
                    return True
            return False

        allowed_medicines = {}
        medicines = self.get_instances(
            None, Medicine, extra_filters={"disease_id": disease_id}
        )
        user = self.get_instances(user_id, User, find_first=True)
        age = user.age
        gender = user.gender
        is_pregnant = user.is_pregnant
        medications = [
            str(medication.detail).lower()
            for medication in self.get_instances(user_id, Medication)
        ]
        conditions = [
            str(condition.detail).lower()
            for condition in self.get_instances(user_id, MedicalCondition)
        ]
        allergies = [str(allergy.detail).lower() for allergy in self.get_instances(user_id, Allergy)]
        surgeries = [
            str(surgery.detail).lower()
            for surgery in self.get_instances(user_id, Surgery)
        ]
        for medicine in medicines:
            if medicine.type not in allowed_medicines:
                allowed_medicines[medicine.type] = []
            if (
                (age < medicine.min_age or age > medicine.max_age)
                or (
                    gender
                    not in medicine.allowed_gender.split(",").map(lambda x: x.strip())
                )
                or (not is_pregnant or medicine.allowed_for_pregnant)
                or (
                    any_word_in_x_match_any_word_in_y(
                        allergies, medicine.not_for_allergies
                    )
                )
                or (
                    any_word_in_x_match_any_word_in_y(
                        conditions, medicine.not_for_conditions
                    )
                )
                or (
                    any_word_in_x_match_any_word_in_y(
                        surgeries, medicine.not_for_surgeries
                    )
                )
                or (
                    any_word_in_x_match_any_word_in_y(
                        medications, medicine.not_for_medications
                    )
                )
            ):
                continue
            allowed_medicines[medicine.type].append(medicine.detail)
        return "\n".join(
            [
                f"{medicine_type}: {', '.join(medicines)}"
                for medicine_type, medicines in allowed_medicines.items()
                if len(medicines) > 0
            ]
        )
