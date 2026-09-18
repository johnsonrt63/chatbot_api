#!/usr/bin/bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SERVICE_API_KEY" \
  -d '{ "session_id": "test-session-1","message": "Explain zero trust in one paragraph" }'
