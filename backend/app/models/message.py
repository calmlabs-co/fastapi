import uuid
from sqlmodel import SQLModel, Field
from typing import Optional

class Message(SQLModel, table=True):
  __tablename__:str = "messages"
  id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
  content: str

  def __repr__(self):
    return f"<Message(id={self.id}, content={self.content})>"
