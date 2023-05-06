from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, unique=True)
    username = Column(Text, nullable=False)
    first_name = Column(Text, default="")
    last_name = Column(Text, default="")
    last_interaction = Column(DateTime, default=datetime.utcnow)
    first_seen = Column(DateTime, default=datetime.utcnow)
    current_dialog_id = Column(Text, default="")
    current_chat_mode = Column(Text, default="default")
    current_model = Column(Text, default="gpt-3.5-turbo")
    n_used_tokens = Column(JSON, default={})
    is_pregnant = Column(Boolean, default=False)
    diagnosed_with = Column(Text, default="")
    age = Column(Text, default="0")
    gender = Column(Text, default="Unknown")
    address = Column(Text, default="Unknown")


class Allergy(Base):
    __tablename__ = "allergy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)
    detail = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class MedicalCondition(Base):
    __tablename__ = "medical_condition"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)
    detail = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Medication(Base):
    __tablename__ = "medication"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)
    detail = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Surgery(Base):
    __tablename__ = "surgery"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)
    detail = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Dialog(Base):
    __tablename__ = "dialog"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(Text, nullable=False)
    user_id = Column(Text, nullable=False)
    chat_mode = Column(Text, default="default")
    start_time = Column(DateTime, default=datetime.utcnow)
    model = Column(Text, default="gpt-3.5-turbo")
    messages = Column(JSON, default=[])


class Disease(Base):
    __tablename__ = "disease"

    id = Column(Integer, primary_key=True, autoincrement=True)
    detail = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class DiseaseQuestion(Base):
    __tablename__ = "disease_question"

    id = Column(Integer, primary_key=True, autoincrement=True)
    detail = Column(Text, nullable=False)
    disease_id = Column(Integer, ForeignKey("disease.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)


class DiseaseAnswer(Base):
    __tablename__ = "disease_answer"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)
    detail = Column(Text, nullable=False)
    question_id = Column(Integer, ForeignKey("disease_question.id"))
    disease_id = Column(Integer, ForeignKey("disease.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)


class DiseaseInstructions(Base):
    __tablename__ = "disease_instruction"

    id = Column(Integer, primary_key=True, autoincrement=True)
    detail = Column(Text, nullable=False)
    disease_id = Column(Integer, ForeignKey("disease.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)


class Medicine(Base):
    __tablename__ = "medicine"

    id = Column(Integer, primary_key=True, autoincrement=True)
    detail = Column(Text, default="")
    type = Column(Text, default="")  # Antibiotic, Decongestant, Steroid, Antifungal
    limit_by = Column(Text, default="")
    limit = Column(Text, default="")
    limit_type = Column(Text, default="")  # greater than, less than, equal to, contains
    disease_id = Column(Integer, ForeignKey("disease.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)


class Disposition(Base):
    __tablename__ = "disposition"

    id = Column(Integer, primary_key=True, autoincrement=True)
    detail = Column(Text, nullable=False)
    disease_id = Column(Integer, ForeignKey("disease.id"))
    user_id = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
