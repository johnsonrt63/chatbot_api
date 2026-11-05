# Chatbot API

A FastAPI-based chatbot API with optional header authentication, in-memory session tracking, a simple CLI client, and a browser UI.

## Files

- `app.py` — FastAPI application
- `static/index.html` — graphical chat web interface
- `client.py` — CLI client for `/chat`
- `system_prompt.txt` — default system prompt (used when `SYSTEM_PROMPT` is unset)
- `requirements.txt` — Python dependencies
- `Dockerfile` — container image definition

## Environment variables

- `OPENAI_API_KEY` — required for model calls
- `OPENAI_MODEL` — optional model name (default: `gpt-4o-mini`)
- `SERVICE_API_KEY` — optional; when set, chatbot requests must send `X-API-Key`
- `SYSTEM_PROMPT` — optional default system prompt; overrides `system_prompt.txt` when set

## Authentication header

When `SERVICE_API_KEY` is set, chatbot requests must include:

- Header: `X-API-Key: <your service api key>`

## Web UI

Open the root URL after starting the server:

- `GET /` — chat page

The page lets you:

1. Enter a user prompt and receive a chatbot reply
2. Optionally enter a system prompt that overrides the file/env default for that session

## Chat endpoint

- `POST /chat`

### Request payload shape

```json
{
  "message": "Hello",
  "session_id": "demo-session",
  "system_prompt": "Optional override for this session"
}
```

`system_prompt` is optional. When provided, it replaces the file/env system prompt for that `session_id`. Changing it clears that session’s history so the new instructions take effect.

### Response payload shape

```json
{"reply":"..."}
```

## Other endpoints

- `GET /health` — liveness check
- `GET /config` — public UI bootstrap info (`auth_required`, `default_system_prompt`)
- `POST /open-session` — create/reset a session (`session_id`, optional `system_prompt`)
- `POST /close-session` — drop a session’s memory

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export OPENAI_API_KEY="sk-..."
export SERVICE_API_KEY="secret123"   # optional
export SYSTEM_PROMPT="You are a concise assistant."  # optional

uvicorn app:app --host 0.0.0.0 --port 8000
```

Then open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) for the UI.

## curl example

```bash
curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secret123" \
  -d '{
    "message":"Hello",
    "session_id":"demo-session",
    "system_prompt":"Answer in one short sentence."
  }'
```

## CLI client

```bash
python client.py chat --api-key "secret123" --session-id "demo-session" "Hello"
python client.py health
```

## Docker

```bash
docker build -t chatbot-api .
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e SERVICE_API_KEY="secret123" \
  -e SYSTEM_PROMPT="You are a helpful assistant." \
  chatbot-api
```
