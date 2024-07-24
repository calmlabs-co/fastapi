from datetime import datetime
from sqlmodel import SQLModel, Field, JSON
import uuid
from typing import  Optional

class User(SQLModel, table=True):
  __tablename__ = "users"
  id: uuid.UUID = Field(default=uuid.uuid4, primary_key=True)
  created_at: datetime = Field(default=datetime.now)
  slack_user_id: str = Field(unique=True)
  slack_installation_settings: Optional[dict] = Field(nullable=True, sa_type=JSON, default={})
