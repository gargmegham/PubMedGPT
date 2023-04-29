from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, Text
from sqlalchemy.ext.declarative import declarative_base

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
    current_model = Column(Text, default="gpt-3.5-turbo")
    n_used_tokens = Column(JSON, default={})
    age = Column(Integer, default=0)
    gender = Column(Text, default="Unknown")
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
    model = Column(Text, default="gpt-3.5-turbo")
    messages = Column(JSON, default=[])


class SinusCongestionQnA(Base):
    __tablename__ = "sinus_congestion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    question = Column(Text, default="")
    answer = Column(Text, default="")
    timestamp = Column(DateTime, default=datetime.utcnow)
