#!/bin/bash
curl -X POST http://localhost:8000/chat   -H "Content-Type: application/json"   -H "X-API-Key: $SERVICE_API_KEY" -d '{
    "message": "Explain zero trust simply",
    "session_id": "000-001"
  }'
