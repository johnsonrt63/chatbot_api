# Chatbot API

FastAPI chatbot service with fixed `X-API-Key` authentication, environment-driven system prompt initialization, in-memory session state, and a small CLI client.

## Environment variables

- `SERVICE_API_KEY` — required API key checked against the `X-API-Key` header.
- `SYSTEM_PROMPT` — required default system prompt captured when a session is opened.

## Run locally

```bash
export SERVICE_API_KEY=my-secret-key
export SYSTEM_PROMPT="You are a helpful assistant."
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /health`
- `POST /open-session` with `{ "session_id": "abc" }`
- `POST /chat` with `{ "session_id": "abc", "message": "Hello" }`
- `POST /close-session` with `{ "session_id": "abc" }`

## CLI examples

```bash
python client.py --api-key my-secret-key open-session demo
python client.py --api-key my-secret-key chat demo "Hello there"
python client.py --api-key my-secret-key close-session demo
```

## Docker

```bash
docker build -t chatbot-api .
docker run -p 8000:8000 \
  -e SERVICE_API_KEY=my-secret-key \
  -e SYSTEM_PROMPT="You are a helpful assistant." \
  chatbot-api
```
