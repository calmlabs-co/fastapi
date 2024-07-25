from fastapi import APIRouter, HTTPException, Depends
from typing import Dict
from sqlmodel import Session, select
from backend.app.models.user import User
from backend.app.dependencies.database import get_sync_db, Session
from fastapi import Request

router = APIRouter()

@router.get("/slack/{slack_user_id}/settings")
async def get_user_settings(slack_user_id: str, session: Session = Depends(get_sync_db), response_model=User):
    statement = select(User).filter_by(slack_user_id=slack_user_id)
    user = session.scalars(statement).first()
    if not user:
      raise HTTPException(status_code=404, detail="User settings not found")
    return user

@router.post("slack/{slack_user_id}/settings")
async def set_user_settings(slack_user_id: str, request: Request, session: Session = Depends(get_sync_db), response_model=User):
  statement = select(User).filter_by(slack_user_id=slack_user_id)
  user = session.scalars(statement).first()
  if not user:
    raise HTTPException(status_code=404, detail="User not found")
  json = await request.json()
  if json:
    user.slack_installation_settings = json
    session.add(user)
    session.commit()
    session.refresh(user)
  return user
