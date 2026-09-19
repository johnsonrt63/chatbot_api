import os
from typing import Dict, List

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict

try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:  # pragma: no cover - compatibility fallback
    LANGCHAIN_AVAILABLE = False


app = FastAPI(title="Chatbot API")

sessions: Dict[str, List[object]] = {}


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    session_id: str


class ChatResponse(BaseModel):
    reply: str


def require_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
    expected = os.getenv("SERVICE_API_KEY")
    if not expected:
        raise HTTPException(status_code=500, detail="SERVICE_API_KEY is not configured")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")


def build_system_prompt() -> str:
    system_prompt = os.getenv("SYSTEM_PROMPT")
    if system_prompt is None:
        raise HTTPException(status_code=500, detail="SYSTEM_PROMPT is not configured")
    return system_prompt


def create_session(session_id: str) -> List[object]:
    history: List[object] = []
    system_prompt = build_system_prompt()
    if LANGCHAIN_AVAILABLE:
        history.append(SystemMessage(content=system_prompt))
    else:
        history.append({"role": "system", "content": system_prompt})
    sessions[session_id] = history
    return history


def get_or_create_session(session_id: str) -> List[object]:
    if session_id not in sessions:
        return create_session(session_id)
    return sessions[session_id]


def generate_reply(history: List[object], message: str) -> str:
    if LANGCHAIN_AVAILABLE:
        history.append(HumanMessage(content=message))
        system_prompt = history[0].content
        prior_turns = []
        for item in history[1:-1]:
            role = "assistant" if isinstance(item, AIMessage) else "user"
            prior_turns.append(f"{role}: {item.content}")
        prior_context = " | ".join(prior_turns[-6:]) if prior_turns else "no prior conversation"
        reply = (
            f"{system_prompt} | session-aware reply to: {message}"
            f" | context: {prior_context}"
        )
        history.append(AIMessage(content=reply))
        return reply

    history.append({"role": "user", "content": message})
    system_prompt = history[0]["content"]
    prior_turns = [f"{item['role']}: {item['content']}" for item in history[1:-1]]
    prior_context = " | ".join(prior_turns[-6:]) if prior_turns else "no prior conversation"
    reply = f"{system_prompt} | session-aware reply to: {message} | context: {prior_context}"
    history.append({"role": "assistant", "content": reply})
    return reply


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, _: None = Depends(require_api_key)) -> ChatResponse:
    history = get_or_create_session(request.session_id)
    reply = generate_reply(history, request.message)
    return ChatResponse(reply=reply)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
