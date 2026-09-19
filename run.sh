#!/usr/bin/bash
docker run -p 8000:8000 \
-e OPENAI_API_KEY= "$OPEN_API_KEY" \
-e OPENAI_MODEL=gpt-4o-mini \
-e SERVICE_API_KEY=$SERVICE_API_KEY \
-e SYSTEM_PROMPT="You are a helpful assistant." \
chatbot-api
