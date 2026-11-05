from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

STATIC_DIR = Path(__file__).resolve().parent / "static"
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."


def load_default_system_prompt() -> str:
    """Prefer SYSTEM_PROMPT env, then system_prompt.txt, then a built-in default."""
    env_prompt = os.getenv("SYSTEM_PROMPT")
    if env_prompt and env_prompt.strip():
        return env_prompt.strip()

    file_path = Path("system_prompt.txt")
    if file_path.exists():
        return file_path.read_text(encoding="utf-8").strip() or DEFAULT_SYSTEM_PROMPT

    return DEFAULT_SYSTEM_PROMPT


default_system_prompt = load_default_system_prompt()
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
service_api_key = os.getenv("SERVICE_API_KEY")

app = FastAPI(title="LangChain Chatbot API")

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "{system_prompt}"),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ]
)

# session_id -> chat history
sessions_db: dict[str, InMemoryChatMessageHistory] = {}
# session_id -> active system prompt for that conversation
session_prompts: dict[str, str] = {}
_conversational_chain = None


def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in sessions_db:
        sessions_db[session_id] = InMemoryChatMessageHistory()
    return sessions_db[session_id]


def get_conversational_chain():
    """Build the LangChain runnable lazily so the UI can start without credentials."""
    global _conversational_chain
    if _conversational_chain is not None:
        return _conversational_chain
    if not openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured on the server",
        )
    model = ChatOpenAI(
        model=openai_model,
        temperature=0.7,
        openai_api_key=openai_api_key,
    )
    _conversational_chain = RunnableWithMessageHistory(
        prompt | model,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history",
    )
    return _conversational_chain


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    system_prompt: Optional[str] = Field(
        default=None,
        description="Optional override used instead of the file/env system prompt.",
    )


class SessionRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    system_prompt: Optional[str] = None


def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    """Enforce X-API-Key when SERVICE_API_KEY is configured."""
    if not service_api_key:
        return
    if x_api_key != service_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def resolve_system_prompt(session_id: str, override: Optional[str]) -> str:
    """
    Use an explicit override when provided; otherwise keep the session prompt
    or fall back to the default loaded at startup.
    """
    if override is not None and override.strip():
        prompt_text = override.strip()
        # Changing the system prompt starts a fresh conversation for that session.
        if session_prompts.get(session_id) != prompt_text:
            sessions_db[session_id] = InMemoryChatMessageHistory()
        session_prompts[session_id] = prompt_text
        return prompt_text

    if session_id in session_prompts:
        return session_prompts[session_id]

    session_prompts[session_id] = default_system_prompt
    return default_system_prompt


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/config")
async def public_config() -> dict:
    """Non-secret settings the web UI needs on load."""
    return {
        "auth_required": bool(service_api_key),
        "default_system_prompt": default_system_prompt,
    }


@app.post("/open-session")
async def open_session(
    payload: SessionRequest,
    _: None = Depends(require_api_key),
) -> dict:
    get_session_history(payload.session_id)
    prompt_text = (
        payload.system_prompt.strip()
        if payload.system_prompt and payload.system_prompt.strip()
        else default_system_prompt
    )
    session_prompts[payload.session_id] = prompt_text
    return {
        "session_id": payload.session_id,
        "system_prompt": prompt_text,
        "status": "open",
    }


@app.post("/close-session")
async def close_session(
    payload: SessionRequest,
    _: None = Depends(require_api_key),
) -> dict:
    sessions_db.pop(payload.session_id, None)
    session_prompts.pop(payload.session_id, None)
    return {"session_id": payload.session_id, "status": "closed"}


@app.post("/chat")
async def chat_endpoint(
    payload: ChatRequest,
    _: None = Depends(require_api_key),
) -> dict:
    """
    Accepts a session_id and a message string.
    Optional system_prompt overrides the file/env default for that session.
    """
    system_prompt = resolve_system_prompt(payload.session_id, payload.system_prompt)
    response = get_conversational_chain().invoke(
        {"input": payload.message, "system_prompt": system_prompt},
        config={"configurable": {"session_id": payload.session_id}},
    )
    return {"reply": response.content}


@app.get("/")
async def index() -> FileResponse:
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Web UI not found")
    return FileResponse(index_path)


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
