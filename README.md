# Chatbot API

A FastAPI-based chatbot API with fixed header authentication, in-memory session tracking, and a simple CLI client.

## Files

- `app.py` - FastAPI application
- `client.py` - CLI client for `/chat`
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container image definition

## Environment variables

- `SERVICE_API_KEY` - required API key checked against the `X-API-Key` header
- `SYSTEM_PROMPT` - required system prompt used only when a new session is first created

## Authentication header

All chatbot requests must include:

- Header: `X-API-Key: <your service api key>`

## Chat endpoint

There is a single chatbot communication endpoint:

- `POST /chat`

### Request payload shape

```json
{"message":"{message}","session_id":"{session_id}"}
```

If `session_id` does not exist yet, the API automatically creates a new in-memory session and starts tracking it.

### Response payload shape

```json
{"reply":"..."}
```

For AIRT, the JSON response path is:

```text
$.reply
```

## Optional health endpoint

- `GET /health`

## Run locally

```bash
export SERVICE_API_KEY="secret123"
export SYSTEM_PROMPT="You are a concise assistant."
uvicorn app:app --host 0.0.0.0 --port 8000
```

## curl example

```bash
curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secret123" \
  -d '{"message":"Hello","session_id":"demo-session"}'
```

Example response:

```json
{"reply":"..."}
```

## CLI client

Send a message:

```bash
python client.py chat --api-key "secret123" --session-id "demo-session" "Hello"
```

Check health:

```bash
python client.py health
```

## Docker

Build and run:

```bash
docker build -t chatbot-api .
docker run --rm -p 8000:8000 \
  -e SERVICE_API_KEY="secret123" \
  -e SYSTEM_PROMPT="You are a concise assistant." \
  chatbot-api
```
