from sqlmodel import SQLModel, Field
import uuid
from datetime import datetime


class User(SQLModel, table=True):
  __tablename__ = "users"
  id: uuid.UUID = Field(default=uuid.uuid4, primary_key=True)
  created_at: datetime = Field(default=datetime.now)
