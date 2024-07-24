from slack_sdk.web import WebClient
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import PlainTextResponse
from slack_sdk.web import WebClient
from backend.app.oauth.v2.endpoints.install import state_store, installation_store
from slack_sdk.oauth.installation_store import Installation
from backend.app.core.init_settings import global_settings
import html
import os

router = APIRouter()

async def create_user_and_link_to_slack(slack_user_id: str):
  from backend.app.models.user import User
  from backend.app.dependencies.database import get_session
  from sqlmodel import select

  async with get_session() as session:
    # Check if the user already exists
    statement = select(User).where(User.slack_user_id == slack_user_id)
    results = await session.exec(statement)
    user = results.first()

    if not user:
      # Create a new user if it doesn't exist
      user = User(slack_user_id=slack_user_id)
      session.add(user)
      await session.commit()
      await session.refresh(user)

    return user


@router.get("/slack/callback")
async def oauth_callback(request: Request):
  # Retrieve the auth code and state from the request params
  code = request.query_params.get("code")
  state = request.query_params.get("state")
  if code:
    # Verify the state parameter
    if state_store.consume(state):
      client = WebClient()  # no prepared token needed for this
      # Complete the installation by calling oauth.v2.access API method
      oauth_response = client.oauth_v2_access(
        client_id=os.getenv('SLACK_CLIENT_ID'),
        client_secret=os.getenv('SLACK_CLIENT_SECRET'),
        redirect_uri=os.getenv('SLACK_REDIRECT_URI'),
        code=code
      )
      installed_enterprise = oauth_response.get("enterprise") or {}
      is_enterprise_install = oauth_response.get("is_enterprise_install")
      installed_team = oauth_response.get("team") or {}
      installer = oauth_response.get("authed_user") or {}
      incoming_webhook = oauth_response.get("incoming_webhook") or {}
      bot_token = oauth_response.get("access_token")
      # NOTE: oauth.v2.access doesn't include bot_id in response
      bot_id = None
      enterprise_url = None
      if bot_token is not None:
        auth_test = client.auth_test(token=bot_token)
        bot_id = auth_test["bot_id"]
        if is_enterprise_install is True:
          enterprise_url = auth_test.get("url")

      installation = Installation(
        app_id=oauth_response.get("app_id"),
        enterprise_id=installed_enterprise.get("id"),
        enterprise_name=installed_enterprise.get("name"),
        enterprise_url=enterprise_url,
        team_id=installed_team.get("id"),
        team_name=installed_team.get("name"),
        bot_token=bot_token,
        bot_id=bot_id,
        bot_user_id=oauth_response.get("bot_user_id"),
        bot_scopes=oauth_response.get("scope"),  # comma-separated string
        user_id=installer.get("id"),
        user_token=installer.get("access_token"),
        user_scopes=installer.get("scope"),  # comma-separated string
        incoming_webhook_url=incoming_webhook.get("url"),
        incoming_webhook_channel=incoming_webhook.get("channel"),
        incoming_webhook_channel_id=incoming_webhook.get("channel_id"),
        incoming_webhook_configuration_url=incoming_webhook.get("configuration_url"),
        is_enterprise_install=is_enterprise_install,
        token_type=oauth_response.get("token_type"),
      )
      # Store the installation
      installation_store.save(installation)
      create_user_and_link_to_slack(installer.get("id"))

      return PlainTextResponse("Installation successful!")
    else:
      raise HTTPException(status_code=400, detail="Try the installation again (the state value is already expired)")

  error = request.query_params.get("error", "")
  raise HTTPException(status_code=400, detail=f"Something is wrong with the installation (error: {html.escape(error)}")