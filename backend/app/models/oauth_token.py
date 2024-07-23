from sqlmodel import SQLModel, Field

class OAuthToken(SQLModel, table=True):
  __tablename__ = "oauth_tokens"
  id: int = Field(default=None, primary_key=True)
  user_id: str
  access_token: str
  refresh_token: str = None
  token_type: str = None
  scope: str = None
  expires_in: int = None
  received_at: int = None
