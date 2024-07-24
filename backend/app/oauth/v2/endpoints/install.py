import os
import html
from slack_sdk.oauth import AuthorizeUrlGenerator
from slack_sdk.oauth.installation_store.sqlalchemy import SQLAlchemyInstallationStore
from slack_sdk.oauth.state_store.sqlalchemy import SQLAlchemyOAuthStateStore
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from backend.app.core.constants import bot_scopes, user_scopes
import sqlalchemy
from sqlalchemy.engine import Engine


engine: Engine = sqlalchemy.create_engine(os.getenv('DATABASE_URL'))
# Issue and consume state parameter value on the server-side.
state_store = SQLAlchemyOAuthStateStore(
  expiration_seconds=300, 
  engine=engine,
)

# Persist installation data and lookup it by IDs.
installation_store = SQLAlchemyInstallationStore(
  client_id=os.getenv('SLACK_CLIENT_ID'),
  engine=engine,
)

try:
  engine.execute("select count(*) from slack_bots")
except Exception as e:
  installation_store.metadata.create_all(engine)
  state_store.metadata.create_all(engine)

# Build https://slack.com/oauth/v2/authorize with sufficient query parameters
authorize_url_generator = AuthorizeUrlGenerator(
  client_id=os.getenv('SLACK_CLIENT_ID'),
  scopes=bot_scopes,
  user_scopes=user_scopes,
  redirect_uri=os.getenv('SLACK_REDIRECT_URI')
)

router = APIRouter()

@router.get("/slack/install", response_class=HTMLResponse)
async def oauth_start():
  # Generate a random value and store it on the server-side
  state = state_store.issue()
  # https://slack.com/oauth/v2/authorize?state=(generated value)&client_id={client_id}&scope=app_mentions:read,chat:write&user_scope=search:read
  url = authorize_url_generator.generate(state)
  return HTMLResponse(content=f'<a href="{html.escape(url)}">'
                f'<img alt="Add to Slack" height="40" width="139" src="https://platform.slack-edge.com/img/add_to_slack.png" srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x" /></a>')