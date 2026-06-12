from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime


class PlanStep(BaseModel):
    step: int
    tool: str
    description: str
    result_preview: Optional[str] = None
    success: bool


class AgentResult(BaseModel):
    session_id: str
    status: str  # success | needs_clarification | error
    clarification_question: Optional[str] = None
    extracted_text: Optional[str] = None
    plan_trace: List[PlanStep] = []
    final_answer: Optional[str] = None
    cost_estimate: Optional[str] = None
    duration_seconds: Optional[float] = None


class ConversationEntry(BaseModel):
    id: str
    session_id: str
    role: str  # user | assistant
    content: str
    files: List[str] = []
    plan_trace: List[PlanStep] = []
    timestamp: str


class ClarificationInput(BaseModel):
    session_id: str
    clarification: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


# In-memory session store (keyed by session_id)
sessions: dict[str, dict] = {}
conversation_history: list[ConversationEntry] = []


def get_or_create_session(session_id: str) -> dict:
    if session_id not in sessions:
        sessions[session_id] = {
            "id": session_id,
            "pending_clarification": None,
            "context": "",
        }
    return sessions[session_id]
