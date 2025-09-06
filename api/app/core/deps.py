from typing import Generator
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, get_db

def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()