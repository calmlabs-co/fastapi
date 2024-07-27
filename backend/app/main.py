import logging
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.app.core.init_settings import args, global_settings
from backend.app.api.v1.endpoints import message, doc, base
from backend.app.dependencies.database import init_db, AsyncSessionLocal
from backend.data.init_data import models_data
from backend.app.oauth.v2.endpoints import install, callback
from backend.app.api.v1.endpoints import users
from slack_bolt.adapter.fastapi import SlackRequestHandler
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt import App

# Create a logger
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
  # Initialize the database connection
  init_db()
  yield

# Start of Slack Bolt setup
slack_bolt_app = App(
  token=os.environ.get("SLACK_BOT_TOKEN"),
  signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
  logger=logger,
  oauth_settings=OAuthSettings(
    client_id=os.environ.get("SLACK_CLIENT_ID"),
    client_secret=os.environ.get("SLACK_CLIENT_SECRET"),
    state_store=install.oauth_state_store
  ),
  installation_store=install.installation_store
)
# app_handler = SlackRequestHandler(slack_bolt_app)
app_handler = SocketModeHandler(slack_bolt_app, os.environ.get("SLACK_APP_TOKEN")).connect()

@slack_bolt_app.message("hello")
def handle_message_event(message, say):
  print(message)
  say(
    blocks=[
      {
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"Hey there <@{message['user']}>!"},
        "accessory": {
            "type": "button",
            "text": {"type": "plain_text", "text": "Click Me"},
            "action_id": "button_click"
        }
      }
    ],
    text=f"Hey there <@{message['user']}>!"
  )

@slack_bolt_app.event("message")
def handle_message(body, say, logger):
  logger.info(body)
  say("Message!! 👋")

@slack_bolt_app.event("app_mention")
def handle_app_mention_events(body, say, logger):
  print(body)
  logger.info(body)
  say("App mention!! 👋")

# The open_modal shortcut listens to a shortcut with the callback_id "change_settings_open_modal"
@slack_bolt_app.shortcut('change_settings_open_modal')
def open_change_settings_modal(ack, shortcut, client):
    # Acknowledge the shortcut request
    ack()
    # Call the views_open method using the built-in WebClient
    client.views_open(
        trigger_id=shortcut["trigger_id"],
        # A simple view payload for a modal
        view={
          "title": {
            "type": "plain_text",
            "text": "Ketchup Settings"
          },
          "submit": {
            "type": "plain_text",
            "text": "Submit",
          },
          "type": "modal",
          "close": {
            "type": "plain_text",
            "text": "Cancel",
          },
          "blocks": [
            {
              "type": "input",
              "block_id": "main_settings",
              "element": {
                "type": "checkboxes",
                "initial_options": [
                  {
                    "text": {
                      "type": "plain_text",
                      "text": "The Direct Messages that I am in",
                    },
                    "value": "direct_messages"
                  },
                  {
                    "text": {
                      "type": "plain_text",
                      "text": "Messages that I am directly mentioned in",
                    },
                    "value": "direct_mentions"
                  },
                  {
                    "text": {
                      "type": "plain_text",
                      "text": "Messages that I am mentioned in via a User Group",
                    },
                    "value": "user_group_mentions"
                  }
                ],
                "options": [
                  {
                    "text": {
                      "type": "plain_text",
                      "text": "The Direct Messages that I am in",
                    },
                    "value": "direct_messages"
                  },
                  {
                    "text": {
                      "type": "plain_text",
                      "text": "Messages that I am directly mentioned in",
                    },
                    "value": "direct_mentions"
                  },
                  {
                    "text": {
                      "type": "plain_text",
                      "text": "Messages that I am mentioned in via a User Group",
                    },
                    "value": "user_group_mentions"
                  }
                ]
              },
              "label": {
                "type": "plain_text",
                "text": "Tick the checkboxes on what you want to get a summary of:",
              }
            },
            {
              "type": "section",
              "block_id": "followed_channels",
              "text": {
                "type": "mrkdwn",
                "text": ":speech_balloon: *Channels I want to follow*"
              },
              "accessory": {
                "type": "multi_channels_select",
                "max_selected_items": 10,
                "placeholder": {
                  "type": "plain_text",
                  "text": "Select channels"
                }
              }
            },
            {
              "type": "section",
              "block_id": "followed_users",
              "text": {
                "type": "mrkdwn",
                "text": ":busts_in_silhouette: *People I want to follow*"
              },
              "accessory": {
                "type": "multi_users_select",
                "max_selected_items": 5,
                "placeholder": {
                  "type": "plain_text",
                  "text": "Select users"
                }
              }
            },
            {
              "type": "divider"
            },
            {
              "type": "section",
              "block_id": "days_to_send",
              "text": {
                "type": "mrkdwn",
                "text": ":timer_clock: *How often and when would you like to receive the summary?*"
              },
              "accessory": {
                "type": "multi_static_select",
                "placeholder": {
                  "type": "plain_text",
                  "text": "Select days"
                },
                "initial_options": [
                  {
                    "text": {
                      "type": "plain_text",
                      "text": "Monday",
                    },
                    "value": "monday"
                  },
                  {
                    "text": {
                      "type": "plain_text",
                      "text": "Tuesday"
                    },
                    "value": "tuesday"
                  },
                  {
                    "text": {
                      "type": "plain_text",
                      "text": "Wednesday"
                    },
                    "value": "wednesday"
                  },
                  {
                    "text": {
                      "type": "plain_text",
                      "text": "Thursday"
                    },
                    "value": "thursday"
                  },
                  {
                    "text": {
                      "type": "plain_text",
                      "text": "Friday"
                    },
                    "value": "friday"
                  }
                ],
                "options": [
                  {
                    "text": {
                      "type": "plain_text",
                      "text": "Monday",
                    },
                    "value": "monday"
                  },
                  {
                    "text": {
                      "type": "plain_text",
                      "text": "Tuesday"
                    },
                    "value": "tuesday"
                  },
                  {
                    "text": {
                      "type": "plain_text",
                      "text": "Wednesday"
                    },
                    "value": "wednesday"
                  },
                  {
                    "text": {
                      "type": "plain_text",
                      "text": "Thursday"
                    },
                    "value": "thursday"
                  },
                  {
                    "text": {
                      "type": "plain_text",
                      "text": "Friday"
                    },
                    "value": "friday"
                  }
                ]
              }
            },
            {
              "type": "section",
              "block_id": "time_to_send",
              "text": {
                "type": "mrkdwn",
                "text": "Time"
              },
              "accessory": {
                "type": "timepicker",
                "timezone": "America/Los_Angeles",
                "action_id": "timepicker123",
                "initial_time": "09:00",
                "placeholder": {
                  "type": "plain_text",
                  "text": "Select a time"
                }
              }
            }
          ]
        }
    )

@slack_bolt_app.view("change_settings")
def handle_submission(ack, body, client, view, logger):
    user_id = body["user"]["id"]
    
    # TODO: Validate the inputs
    # Assume there's an input block with `input_c` as the block_id and `dreamy_input`
    logger.info(view['state']['values'])
    main_settings = view["state"]["values"]["main_settings"]
    followed_channels = view["state"]["values"]["followed_channels"]
    followed_users = view["state"]["values"]["followed_users"]

    validated_settings = {}
    # errors = {}
    # if hopes_and_dreams is not None and len(hopes_and_dreams) <= 5:
    #     errors["input_c"] = "The value must be longer than 5 characters"
    # if len(errors) > 0:
    #     ack(response_action="errors", errors=errors)
    #     return
    
    # Acknowledge the view_submission request and close the modal
    ack()
    
    # Do whatever you want with the input data - here we're saving it to a DB
    # then sending the user a verification of their submission
    # TODO: update settings of the user
    try:
      user = callback.update_user_settings(user_id, validated_settings)
      user_settings = user.slack_installation_settings
    except Exception as e:
      logger.exception(f"Failed to update user settings")

    try:
      # bring user back to home view with updated settings
      publish_home_view(user_id, user_settings, client, logger)
    except Exception as e:
      logger.exception(f"Failed to post a message {e}")


def publish_home_view(user_id, user_settings, client, logger):
   client.views_publish(
      type="home",
      user_id=user_id,
      view={
        "type": "home",
        "blocks": [
          {
            "type": "header",
            "text": {
              "type": "plain_text",
              "text": ":wave: Welcome to Ketchup!"
            }
          },
          {
            "type": "section",
            "text": {
              "type": "plain_text",
              "text": "Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum"
            }
          },
          {
            "type": "header",
            "text": {
              "type": "plain_text",
              "text": "Your Current Settings"
            }
          },
          {
            "type": "divider"
          },
          {
            "type": "section",
            "text": {
              "type": "plain_text",
              "text": ":white_tick: I want to summarize my Direct messages."
            }
          },
          {
            "type": "section",
            "text": {
              "type": "plain_text",
              "text": ":white_tick: I want to summarize the messages and threads that I am directly mentioned in."
            }
          },
          {
            "type": "section",
            "text": {
              "type": "plain_text",
              "text": ":white_tick: I want to summarize the messages and threads that I indirectly mentioned via user groups."
            }
          },
          {
            "type": "section",
            "text": {
              "type": "plain_text",
              "text": ":white_tick: I want to follow the following channels: #product, #engineering…"
            }
          },
          {
            "type": "section",
            "text": {
              "type": "plain_text",
              "text": ":white_tick: I want to follow the following teammates: @abc"
            }
          },
          {
            "type": "section",
            "text": {
              "type": "plain_text",
              "text": ":timer: I will receive the summaries via DM on: \nMonday, Tuesday, Wednesday, Thursday, Friday @ 9:00AM"
            }
          },
          {
            "type": "actions",
            "elements": [
              {
                "type": "button",
                "text": {
                  "type": "plain_text",
                  "text": ":gear: Change Settings",
                },
                "action_id": "change_settings_open_modal"
              }
            ]
          },
          {
            "type": "header",
            "text": {
              "type": "plain_text",
              "text": "Other actions"
            }
          },
          {
            "type": "actions",
            "elements": [
              {
                "type": "button",
                "text": {
                  "type": "plain_text",
                  "text": ":heavy_plus_symbol: Invite Teammates",
                },
                "action_id": "invite_teammates_open_modal"
              },
              {
                "type": "button",
                "text": {
                  "type": "plain_text",
                  "text": ":question: Give us Feedback",
                },
                "action_id": "give-feedback"
              }
            ]
          }
        ]
      }
    )

@slack_bolt_app.event("app_home_opened")
def update_home_tab(client, event, logger):
  logger.info(event)
  user_id = event["user"]

  try:
    # get user settings
    user = callback.get_user_by_slack_user_id(user_id)
    user_settings = user.slack_installation_settings
    
    # publish home view
    publish_home_view(user_id, user_settings, client, logger)
  except Exception as e:
    logger.error(f"Error publishing home tab: {e}")

# Start of FastAPI routes
app = FastAPI(lifespan=lifespan)

# Frontend
templates = Jinja2Templates(directory="frontend/login/templates")
app.mount("/static", StaticFiles(directory="frontend/login/static"), name="static")

# Set Middleware
# Define the allowed origins
origins = [
  global_settings.API_BASE_URL,
  "http://localhost",
  "http://localhost:5000",
]

# Add CORS middleware
app.add_middleware(
  CORSMiddleware,
  allow_origins=origins,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# Add Document protection middleware
@app.middleware("http")
async def add_doc_protect(request: Request, call_next):
  if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
    if not request.session.get('authenticated'):
      return RedirectResponse(url="/login")
  response = await call_next(request)
  return response
# Add session middleware with a custom expiration time (e.g., 30 minutes)
app.add_middleware(SessionMiddleware, 
           secret_key=os.environ.get('SECRET_KEY'), 
           max_age=18000)  # 18000 seconds = 300 minutes

# Add the routers to the FastAPI app
app.include_router(base.router, prefix="", tags=["main"])
app.include_router(doc.router, prefix="", tags=["doc"])
app.include_router(message.router, prefix="/api/v1", tags=["message"])
app.include_router(users.router, prefix="/api/v1/users", tags=["user_settings"])
app.include_router(install.router, prefix="/oauth/v2", tags=["install"])
app.include_router(callback.router, prefix="/oauth/v2", tags=["callback"])

@app.post("/slack/events")
async def handle_slack_events(request: Request):
  return await app_handler.handle(request)

@app.get("/slack/install")
async def install(req: Request):
    return await app_handler.handle(req)

@app.get("/slack/oauth_redirect")
async def oauth_redirect(req: Request):
    return await app_handler.handle(req)

from slack_sdk import WebClient
client = WebClient()

if __name__ == "__main__":
  # mounting at the root path
  uvicorn.run(
    app="backend.app.main:app",
    host = args.host,
    port=int(os.getenv("PORT", 5000)),
    reload=args.mode == "dev"  # Enables auto-reloading in development mode
  )