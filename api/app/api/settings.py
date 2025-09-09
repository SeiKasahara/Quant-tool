from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Dict
import json
from pathlib import Path
import re

from app.services.fuse import signal_fuser
from app.api import auth as auth_api

router = APIRouter()

CONFIG_DIR = Path(__file__).resolve().parents[1] / 'configs'
GLOBAL_CONFIG_PATH = CONFIG_DIR / 'fuser_settings.json'

def _user_config_path(username: str) -> Path:
    safe = re.sub(r'[^a-zA-Z0-9_.-]', '_', username)
    return CONFIG_DIR / f'fuser_settings.{safe}.json'

class WeightsModel(BaseModel):
    W_SRC: float
    W_NOVEL: float
    W_EVT: float
    W_BUZZ: float
    K_CONS: float
    K_UNC: float
    TAU: float

class SettingsModel(BaseModel):
    weights: WeightsModel
    source_weights: Dict[str, float]
    event_priors: Dict[str, float]


def _read(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


@router.get('/settings')
def get_settings(request: Request):
    # try user-specific config first
    sid = request.cookies.get('session')
    user = auth_api._get_session_data(sid) if sid else None
    if user:
        user_path = _user_config_path(user['username'])
        data = _read(user_path)
        if data:
            return data

    # fallback to global
    data = _read(GLOBAL_CONFIG_PATH)
    if data is None:
        # build from current runtime
        data = {
            'weights': {
                'W_SRC': signal_fuser.w_src,
                'W_NOVEL': signal_fuser.w_novel,
                'W_EVT': signal_fuser.w_evt,
                'W_Buzz': signal_fuser.w_buzz,
                'K_CONS': signal_fuser.k_cons,
                'K_UNC': signal_fuser.k_unc,
                'TAU': signal_fuser.tau
            },
            'source_weights': signal_fuser.source_weights,
            'event_priors': signal_fuser.event_priors
        }
    return data


@router.put('/settings')
def put_settings(request: Request, settings: SettingsModel):
    data = settings.dict()
    # basic sanity checks: weights sum maybe >0
    total = data['weights']['W_SRC'] + data['weights']['W_NOVEL'] + data['weights']['W_EVT'] + data['weights']['W_BUZZ']
    if total <= 0:
        raise HTTPException(status_code=400, detail='Sum of weights must be > 0')

    # determine user
    sid = request.cookies.get('session')
    user = auth_api._get_session_data(sid) if sid else None

    # require login to save (config is user-bound). Admin writes global and applies runtime.
    if not user:
        raise HTTPException(status_code=401, detail='authentication required to save settings')

    try:
        if user.get('role') == 'admin':
            # admin: write global and apply
            _write(GLOBAL_CONFIG_PATH, data)
            signal_fuser.reload_from_dict(data)
        else:
            # regular user: write per-user file, do not apply to runtime
            path = _user_config_path(user['username'])
            _write(path, data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {'status': 'ok'}
