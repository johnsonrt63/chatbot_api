import os
from typing import Dict, List
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

try:
    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
    from langchain_core.runnables import RunnableLambda
except ImportError:  # pragma: no cover - lightweight fallback for minimal environments
    class BaseMessage:
        def __init__(self, content: str):
            self.content = content

    class HumanMessage(BaseMessage):
        pass

    class AIMessage(BaseMessage):
        pass

    class RunnableLambda:
        def __init__(self, func):
            self.func = func

        def invoke(self, payload: dict):
            return self.func(payload)


app = FastAPI(title="Chatbot API", version="1.0.0")

# In-memory session store. This is intentionally process-local and resets on restart.
SESSIONS: Dict[str, Dict[str, List[BaseMessage] | str]] = {}


class OpenSessionRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("session_id must not be blank")
        return cleaned


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=8000)

    @field_validator("session_id", "message")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be blank")
        return cleaned


class CloseSessionRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("session_id must not be blank")
        return cleaned


class ApiResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: bool
    data: dict


def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server misconfiguration: {name} is required",
        )
    return value


def authenticate(x_api_key: str = Header(default="", alias="X-API-Key")) -> None:
    expected = get_required_env("SERVICE_API_KEY")
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )
    if x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


def build_chat_chain():
    def generate_reply(payload: dict) -> str:
        history: List[BaseMessage] = payload["history"]
        user_message = payload["message"]
        system_prompt = payload["system_prompt"]

        # Deterministic offline responder wrapped in a LangChain runnable.
        prior_user_messages = [m.content for m in history if isinstance(m, HumanMessage)]
        turn_number = len(prior_user_messages) + 1
        context_hint = f" Previous turns in session: {len(history)}." if history else ""
        return (
            f"{system_prompt}\n\n"
            f"Assistant reply #{turn_number}: I received your message: '{user_message}'."
            f"{context_hint}"
        )

    return RunnableLambda(generate_reply)


CHAT_CHAIN = build_chat_chain()


@app.get("/health")
def health_check() -> ApiResponse:
    return ApiResponse(success=True, data={"status": "ok"})


@app.post("/open-session")
def open_session(request: OpenSessionRequest, _: None = Depends(authenticate)) -> ApiResponse:
    if request.session_id in SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session already exists",
        )

    system_prompt = get_required_env("SYSTEM_PROMPT")
    SESSIONS[request.session_id] = {
        "system_prompt": system_prompt,
        "history": [],
        "created_id": str(uuid4()),
    }
    return ApiResponse(success=True, data={"session_id": request.session_id, "opened": True})


@app.post("/chat")
def chat(request: ChatRequest, _: None = Depends(authenticate)) -> ApiResponse:
    session = SESSIONS.get(request.session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found. Call /open-session first.",
        )

    history = session["history"]
    system_prompt = str(session["system_prompt"])
    assert isinstance(history, list)

    try:
        reply = CHAT_CHAIN.invoke(
            {
                "system_prompt": system_prompt,
                "history": history,
                "message": request.message,
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate reply: {exc}",
        ) from exc

    history.append(HumanMessage(content=request.message))
    history.append(AIMessage(content=str(reply)))

    return ApiResponse(
        success=True,
        data={
            "session_id": request.session_id,
            "reply": str(reply),
            "turns": len(history) // 2,
        },
    )


@app.post("/close-session")
def close_session(request: CloseSessionRequest, _: None = Depends(authenticate)) -> ApiResponse:
    if request.session_id not in SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    del SESSIONS[request.session_id]
    return ApiResponse(success=True, data={"session_id": request.session_id, "closed": True})
