import os, uuid
from typing import Dict

MAX_QUESTIONS = int(os.getenv("MAX_QUESTIONS", "3"))
ADMIN_SESSION_ID = os.getenv("ADMIN_SESSION_ID", "ADMIN-OVERRIDE")

_sessions: Dict[str, int] = {}  # session_id -> questions_asked

def new_session_id() -> str:
    return str(uuid.uuid4())

def add_session(session_id: str) -> None:
    _sessions.setdefault(session_id, 0)

def get_session(session_id: str):
    # returns (session_id, questions_asked) or None
    if session_id in _sessions:
        return (session_id, _sessions[session_id])
    return None

def increment_questions(session_id: str) -> None:
    _sessions[session_id] = _sessions.get(session_id, 0) + 1

def reached_limit(session_id: str) -> bool:
    return _sessions.get(session_id, 0) >= MAX_QUESTIONS

def is_admin(session_id: str) -> bool:
    return session_id == ADMIN_SESSION_ID
