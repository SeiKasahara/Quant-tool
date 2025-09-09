from fastapi import APIRouter, HTTPException
from typing import Dict
import json
from pathlib import Path
import re

from app.nlp.events import event_extractor

CONFIG_PATH = Path(__file__).parents[2] / "configs" / "event_patterns.json"

router = APIRouter()


def _read_patterns() -> Dict[str, list]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read patterns: {e}")


def _write_patterns(data: Dict[str, list]):
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write patterns: {e}")


@router.get("/event-patterns")
async def get_event_patterns():
    """Return current event extraction patterns."""
    return _read_patterns()


@router.put("/event-patterns")
async def update_event_patterns(payload: Dict[str, list]):
    """Replace event extraction patterns and persist to disk."""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be an object mapping event keys to pattern lists")
    # basic validation: values should be lists
    for k, v in payload.items():
        if not isinstance(v, list):
            raise HTTPException(status_code=400, detail=f"Patterns for {k} must be a list")
    # validate each regex before writing to disk
    errors: Dict[str, list] = {}
    has_errors = False
    for k, patterns in payload.items():
        errs = []
        for p in patterns:
            if not isinstance(p, str) or p.strip() == "":
                errs.append("Empty or non-string pattern")
                continue
            try:
                re.compile(p)
            except re.error as e:
                errs.append(str(e))
        if errs:
            errors[k] = errs
            has_errors = True

    if has_errors:
        # return structured validation errors
        raise HTTPException(status_code=400, detail={"validation_errors": errors})

    # all good -> persist and reload
    _write_patterns(payload)
    try:
        event_extractor.reload_patterns()
    except Exception:
        # if reload fails, file persisted; let caller inspect logs or reload later
        pass
    return {"status": "ok", "written": str(CONFIG_PATH)}
