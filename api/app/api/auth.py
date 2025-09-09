from fastapi import APIRouter, Request, Response, HTTPException, Depends
from app.core.config import settings
import redis
import json
from uuid import uuid4
from typing import Optional
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db import models
from datetime import datetime, timedelta
import secrets
import re

router = APIRouter()

# Redis client (synchronous). For production consider using redis.asyncio.
_redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

# password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_session_data(session_id: str) -> Optional[dict]:
    if not session_id:
        return None
    key = f"session:{session_id}"
    raw = _redis.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


@router.post("/auth/register")
async def register(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    username = payload.get("username")
    password = payload.get("password")
    email = payload.get("email")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")

    # basic password strength: >=8, has letter and number
    if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise HTTPException(status_code=400, detail="password must be >=8 chars and include letters and numbers")

    if email:
        # basic email format check
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise HTTPException(status_code=400, detail="invalid email")

    # check existing
    exists = db.query(models.User).filter(models.User.username == username).first()
    if exists:
        raise HTTPException(status_code=400, detail="username already exists")

    hash = pwd_context.hash(password)
    user = models.User(username=username, password_hash=hash, role='user', email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    # generate email token if email provided
    token = None
    if email:
        token = secrets.token_urlsafe(24)
        user.email_token = token
        user.token_expires_at = datetime.utcnow() + timedelta(hours=24)
        db.add(user); db.commit(); db.refresh(user)

    return {"status": "ok", "user": {"username": user.username, "role": user.role}, "email_token": token}


@router.post("/auth/login")
async def login(request: Request, response: Response, db: Session = Depends(get_db)):
    payload = await request.json()
    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not pwd_context.verify(password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")

    # require email confirmation if email set
    if user.email and not user.email_confirmed:
        raise HTTPException(status_code=403, detail="email not confirmed")

    user_info = {
        "username": user.username,
        "role": user.role,
        "avatar": f"https://ui-avatars.com/api/?name={user.username}&background=0D8ABC&color=fff"
    }

    session_id = uuid4().hex
    key = f"session:{session_id}"
    _redis.set(key, json.dumps(user_info), ex=int(settings.SESSION_EXPIRE_SECONDS) if hasattr(settings, 'SESSION_EXPIRE_SECONDS') else 86400)
    response.set_cookie(key="session", value=session_id, httponly=True, path='/', max_age=int(settings.SESSION_EXPIRE_SECONDS) if hasattr(settings, 'SESSION_EXPIRE_SECONDS') else 86400)
    return {"status": "ok", "user": user_info}


@router.post('/auth/confirm')
async def confirm(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    token = payload.get('token')
    if not token:
        raise HTTPException(status_code=400, detail='token required')
    user = db.query(models.User).filter(models.User.email_token == token).first()
    if not user:
        raise HTTPException(status_code=404, detail='invalid token')
    if user.token_expires_at and user.token_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail='token expired')
    user.email_confirmed = True
    user.email_token = None
    user.token_expires_at = None
    db.add(user); db.commit(); db.refresh(user)
    return {'status': 'ok'}


@router.get("/auth/me")
async def get_me(request: Request):
    sid = request.cookies.get("session")
    info = _get_session_data(sid)
    if not info:
        return {"authenticated": False}
    return {"authenticated": True, **info}


@router.post("/auth/logout")
async def logout(request: Request, response: Response):
    sid = request.cookies.get("session")
    if sid:
        _redis.delete(f"session:{sid}")
    response.delete_cookie("session", path='/')
    return {"status": "ok"}
