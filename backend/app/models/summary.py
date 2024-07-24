from sqlmodel import SQLModel, Field, JSON
import uuid
from datetime import datetime
from typing import Dict, List, Optional


class Summary(SQLModel, table=True):
  __tablename__ = "summaries"
  id: uuid.UUID = Field(default=uuid.uuid4, primary_key=True)
  created_at: datetime = Field(default=datetime.now)
  user_id: uuid.UUID = Field(foreign_key="users.id")
  content: Optional[dict] = Field(nullable=True, sa_type=JSON)

