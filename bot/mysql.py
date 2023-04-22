import base64
import config
from sqlalchemy import create_engine, Column, Integer, DateTime, Text
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class PromptCompletion(Base):
    __tablename__ = 'prompts'

    id = Column(Integer, primary_key=True)
    prompt = Column(Text, nullable=False)
    completion = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class MySQL:
    def __init__(self):
        self.engine = create_engine(config.MYSQL_URI)
        self.Session = sessionmaker(bind=self.engine)

    def create_prompts_table_if_not_exists(self):
        Base.metadata.create_all(self.engine)
    
    def insert(self, prompt: str, completion: str):
        base64_prompt = base64.b64encode(prompt.encode("utf-8")).decode("utf-8")
        base64_completion = base64.b64encode(completion.encode("utf-8")).decode("utf-8")
        session = self.Session()
        session.add(PromptCompletion(prompt=base64_prompt, completion=base64_completion))
        session.commit()
    
    def extract_data_json(self):
        session = self.Session()
        entries = session.query(PromptCompletion).all()
        session.close()
        jsonl_response = ""
        for entry in entries:
            jsonl_response += f'{{"prompt": "{base64.b64decode(str(entry.prompt)).decode("utf-8")}", "completion": "{base64.b64decode(str(entry.completion)).decode("utf-8")}"}}\n'
        return jsonl_response.encode("utf-8")
