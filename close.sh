#!/usr/bin/bash
curl -X POST http://localhost:8000/close-session \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SERVICE_API_KEY" \
  -d '{ "session_id": "test-session-1"}'
