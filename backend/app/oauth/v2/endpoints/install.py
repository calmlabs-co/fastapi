import os
import html
from slack_sdk.oauth import AuthorizeUrlGenerator
from slack_sdk.oauth.installation_store import FileInstallationStore, Installation
from slack_sdk.oauth.state_store import FileOAuthStateStore
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from backend.app.core.constants import bot_scopes, user_scopes
from backend.app.core.init_settings import global_settings

# Issue and consume state parameter value on the server-side.
state_store = FileOAuthStateStore(expiration_seconds=300, base_dir="./data")
# Persist installation data and lookup it by IDs.
installation_store = FileInstallationStore(base_dir="./data")

# Build https://slack.com/oauth/v2/authorize with sufficient query parameters
authorize_url_generator = AuthorizeUrlGenerator(
  client_id=os.getenv('SLACK_CLIENT_ID'),
  scopes=bot_scopes,
  user_scopes=user_scopes,
  redirect_uri=os.getenv('SLACK_REDIRECT_URI')
)

router = APIRouter()

@router.get("/install", response_class=HTMLResponse)
async def oauth_start():
  # Generate a random value and store it on the server-side
  state = state_store.issue()
  # https://slack.com/oauth/v2/authorize?state=(generated value)&client_id={client_id}&scope=app_mentions:read,chat:write&user_scope=search:read
  url = authorize_url_generator.generate(state)
  return HTMLResponse(content=f'<a href="{html.escape(url)}">'
                f'<img alt="Add to Slack" height="40" width="139" src="https://platform.slack-edge.com/img/add_to_slack.png" srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x" /></a>')