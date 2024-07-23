import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
  # Application settings
  APP_NAME: str = "Ketchup"
  APP_VERSION: str = "0.1.0"

  # class Config:
  #   case_sensitive = True

  @property
  def DATABASE_URL(self):
    url =  os.getenv('DATABASE_URL', '')
    URL_split = url.split("://")
    if len(URL_split) == 1:
      return f"{URL_split[0]}+psycopg2://{URL_split[1]}"
    return url

  @property
  def ASYNC_DATABASE_URL(self):
    if self.DATABASE_URL:
      URL_split = self.DATABASE_URL.split("://")
      return f"{URL_split[0]}+asyncpg://{URL_split[1]}"
    raise ValueError("DATABASE_URL is not set")

  @property
  def API_BASE_URL(self) -> str:
    if self.ENV_MODE == "dev":
      return 'http://localhost:5000/'
    return self.HOST_URL

class DevSettings(Settings):
  # Environment mode: 'dev' or 'prod'
  ENV_MODE: str = 'dev'

  # Database settings for development
  model_config = SettingsConfigDict(env_file=".env", extra='allow')


class ProdSettings(Settings):
  # Environment mode: 'dev' or 'prod'
  ENV_MODE: str = 'prod'

  # Define HOST_URL based on environment mode
  HOST_URL : str = os.getenv('HOST_URL ', '')

def get_settings(env_mode: str = "dev"):
  if env_mode == "dev":
    return DevSettings()
  return ProdSettings()