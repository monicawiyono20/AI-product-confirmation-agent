import uuid
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from agent import graph

app = FastAPI(title="Insurance Product Knowledge Session")

# In-memory session tracker: session_id -> initialized (bool)
sessions: dict[str, bool] = {}

GREETING = (
    "Hello! Welcome to the Insurance Product Knowledge Session.\n\n"
    "I'm your AI assistant. My role is to make sure you fully understand "
    "the insurance product before you proceed with your purchase.\n\n"
    "To get started, please provide the **agent's email address**."
)


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.get("/", response_class=HTMLResponse)
async def chat_page():
    with open("templates/chat.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.post("/chat/start")
async def start_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = False  # not yet initialized in LangGraph
    return {"session_id": session_id, "message": GREETING}


@app.post("/chat/message")
async def chat_message(req: ChatRequest):
    config = {"configurable": {"thread_id": req.session_id}}

    invoke_input: dict = {"messages": [HumanMessage(req.message)]}

    # First message: inject initial state fields
    if not sessions.get(req.session_id, True):
        invoke_input["step"] = "collect_agent_email"
        invoke_input["agent_email"] = ""
        invoke_input["customer_email"] = ""
        invoke_input["explanation_step"] = 0
        sessions[req.session_id] = True

    result = graph.invoke(invoke_input, config=config)

    # Get the last AI message
    last_msg = next(
        (m.content for m in reversed(result["messages"]) if isinstance(m, AIMessage)),
        "Something went wrong. Please try again."
    )

    return {
        "message": last_msg,
        "done": result.get("step") == "done",
    }
