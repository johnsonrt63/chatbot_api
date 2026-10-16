from fastapi import FastAPI
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
import os

def is_opeanai_api_key_valid(api_key: str) -> bool:
    """
    Checks the validity of an OpenAI API key by making a request to list models.
    Returns True if valid, False otherwise.
    """
    # Initialize the client with the provided key
    client = OpenAI(api_key=api_key)
   
    try:
        # Perform a lightweight request to verify the key
        client.models.list()
        return True
    except openai.AuthenticationError:
        # Specific error caught if the API key is incorrect or invalid
        print("Error: Invalid Authentication. Please check your API key.")
        return False
    except openai.APIConnectionError:
        # Caught if the client cannot connect to the server
        print("Error: Could not connect to OpenAI servers.")
        return False
    except openai.OpenAIError as e:
        # Fallback for any other OpenAI-specific exceptions
        print(f"An OpenAI error occurred: {e}")
        return False

#
# Open System Prompt File and load the system prompt
#
file_path = "system_prompt.txt"
if not os.path.exists(file_path):
    raise FileNotFoundError(f"System prompt file '{file_path}' not found. Please create it with the desired system prompt.")
with open("system_prompt.txt", "r") as f:
    system_prompt = f.read().strip()    

app = FastAPI(title="LangChain Chatbot API")
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# 1. Validate the OpenAI API key
test_key = os.getenv("OPENAI_API_KEY")
if is_openai_key_valid(test_key):
    print("The API key is VALID.")
else:
    print("The API key is INVALID.")

model = ChatOpenAI(model=openai_model, temperature=0.7, openai_api_key=openai_api_key)

# 2. Design the Chat Prompt Template with a history placeholder
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
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
