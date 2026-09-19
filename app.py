from fastapi import FastAPI
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
import os

app = FastAPI(title="LangChain Chatbot API")

# 1. Initialize the LLM (Using OpenAI's GPT-4o-mini as an example)
model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0.7, openai_api_key=os.getenv("OPENAI_API_KEY"))

# 2. Design the Chat Prompt Template with a history placeholder
prompt = ChatPromptTemplate.from_messages([
    ("system", os.getenv("SYSTEM_PROMPT", "You are a helpful and polite AI chatbot assistant.")),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

# 3. Combine prompt and model into an LCEL chain
chain = prompt | model

# 4. In-memory dictionary to store session histories
# Note: In production, replace InMemoryChatMessageHistory with a database or Redis
sessions_db = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in sessions_db:
        sessions_db[session_id] = InMemoryChatMessageHistory()
    return sessions_db[session_id]

# 5. Wrap the chain to automatically manage conversational history
conversational_chain = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history"
)

# 6. Define Pydantic request models for the endpoint
class ChatRequest(BaseModel):
    session_id: str
    message: str

@app.post("/chat")
async def chat_endpoint(payload: ChatRequest):
    """
    Accepts a session_id and a message string.
    Maintains independent memory logs unique to each session_id.
    """
    # Invoke the chain with config options matching the expected session
    response = conversational_chain.invoke(
        {"input": payload.message},
        config={"configurable": {"session_id": payload.session_id}}
    )
   
    return {
#        "session_id": payload.session_id,
        "reply": response.content
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
