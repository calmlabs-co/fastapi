from slack_sdk.web import WebClient
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import PlainTextResponse
from slack_sdk.web import WebClient
from backend.app.oauth.v2.endpoints.install import state_store, installation_store
from slack_sdk.oauth.installation_store import Installation
from backend.app.models.user import User
from backend.app.dependencies.database import get_sync_db
from fastapi import Depends
import html
import os
from sqlmodel import select

router = APIRouter()

async def create_user_and_link_to_slack(slack_user_id: str,  db = Depends(get_sync_db)):
  user = await get_user_by_slack_user_id(slack_user_id, db)
  if user:
    print("User already exists")
  else:
    user = User(slack_user_id=slack_user_id)
    db.add(user)
    db.commit()
  return str(user)

async def get_user_by_slack_user_id(slack_user_id: str, db = Depends(get_sync_db)):
  statement = select(User).filter_by(slack_user_id=slack_user_id)
  user = db.scalars(statement).first()
  return user

async def update_user_settings(user_id: str, settings: dict, db = Depends(get_sync_db)):
  user = await get_user_by_slack_user_id(user_id, db)
  if not user:
    raise HTTPException(status_code=404, detail="User not found")
  
  user.slack_installation_settings = settings
  db.add(user)
  db.commit()
  return user


@router.get("/slack/callback")
async def oauth_callback(request: Request):
  code = request.query_params.get("code")
  state = request.query_params.get("state")
  if code:
    if state_store.consume(state):
      oauth_response = await complete_installation(code)
      installation_store.delete_installation(user_id=oauth_response.get("authed_user").get("id"), enterprise_id=oauth_response.get("enterprise").get("id"), team_id=oauth_response.get("team").get("id"))
      installation = create_installation(oauth_response)
      installation_store.save(installation)
      await create_user_and_link_to_slack(installation.user_id)
      return PlainTextResponse("Installation successful!")
    else:
      raise HTTPException(status_code=400, detail="Try the installation again (the state value is already expired)")

  error = request.query_params.get("error", "")
  raise HTTPException(status_code=400, detail=f"Something is wrong with the installation (error: {html.escape(error)}")

async def get_installation(user_id: str, team_id: str, db = Depends(get_sync_db)):
  statement = select(Installation).filter_by(user_id=user_id, team_id=team_id)
  installation = db.scalars(statement).first()
  if not installation:
    raise HTTPException(status_code=404, detail="Installation not found")
  return installation

async def complete_installation(code: str) -> dict:
  client = WebClient()
  oauth_response = client.oauth_v2_access(
    client_id=os.getenv('SLACK_CLIENT_ID'),
    client_secret=os.getenv('SLACK_CLIENT_SECRET'),
    redirect_uri=os.getenv('SLACK_REDIRECT_URI'),
    code=code
  )
  return oauth_response

def create_installation(oauth_response: dict) -> Installation:
  installed_enterprise = oauth_response.get("enterprise") or {}
  is_enterprise_install = oauth_response.get("is_enterprise_install")
  installed_team = oauth_response.get("team") or {}
  installer = oauth_response.get("authed_user") or {}
  incoming_webhook = oauth_response.get("incoming_webhook") or {}
  bot_token = oauth_response.get("access_token")
  bot_id = None
  enterprise_url = None
  if bot_token is not None:
    client = WebClient()
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
  return installation