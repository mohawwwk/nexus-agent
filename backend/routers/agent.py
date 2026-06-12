import uuid
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from app.models import (
    AgentResult,
    ClarificationInput,
    ConversationEntry,
    ErrorResponse,
    conversation_history,
)
from app.agent import run_agent_pipeline
from datetime import datetime, timezone

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run", response_model=AgentResult)
async def run_agent(
    query: str = Form(...),
    session_id: Optional[str] = Form(None),
    files: List[UploadFile] = File(default=[]),
):
    """
    Main agentic endpoint. Accepts text query + optional uploaded files.
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    sid = session_id or str(uuid.uuid4())

    # Read all uploaded files into memory
    file_data = []
    file_names = []
    for upload in files:
        if upload.filename:
            content = await upload.read()
            file_data.append({
                "filename": upload.filename,
                "bytes": content,
                "type": upload.content_type or "application/octet-stream",
            })
            file_names.append(upload.filename)

    # Store user message in history
    user_entry = ConversationEntry(
        id=str(uuid.uuid4()),
        session_id=sid,
        role="user",
        content=query,
        files=file_names,
        plan_trace=[],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    conversation_history.append(user_entry)

    try:
        result = run_agent_pipeline(
            query=query,
            files=file_data,
            session_id=sid,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Store assistant response in history
    assistant_content = result.final_answer or result.clarification_question or "Processing..."
    assistant_entry = ConversationEntry(
        id=str(uuid.uuid4()),
        session_id=sid,
        role="assistant",
        content=assistant_content,
        files=[],
        plan_trace=result.plan_trace,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    conversation_history.append(assistant_entry)

    return result


@router.post("/clarify", response_model=AgentResult)
async def send_clarification(body: ClarificationInput):
    """
    Continue the conversation after a clarification question was asked.
    """
    sid = body.session_id
    clarification = body.clarification.strip()

    if not clarification:
        raise HTTPException(status_code=400, detail="Clarification cannot be empty")

    # Store user clarification in history
    user_entry = ConversationEntry(
        id=str(uuid.uuid4()),
        session_id=sid,
        role="user",
        content=clarification,
        files=[],
        plan_trace=[],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    conversation_history.append(user_entry)

    try:
        result = run_agent_pipeline(
            query=clarification,
            files=[],
            session_id=sid,
            clarification=clarification,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Store assistant response
    assistant_content = result.final_answer or result.clarification_question or "Processing..."
    assistant_entry = ConversationEntry(
        id=str(uuid.uuid4()),
        session_id=sid,
        role="assistant",
        content=assistant_content,
        files=[],
        plan_trace=result.plan_trace,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    conversation_history.append(assistant_entry)

    return result


@router.get("/history", response_model=List[ConversationEntry])
async def get_history():
    """Return conversation history."""
    return conversation_history
