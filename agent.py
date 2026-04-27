import re
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from product_knowledge import SECTIONS, SUPPORTING_DOCS, PRODUCT_SCRIPT

load_dotenv()

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.4)

EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    agent_email: str
    customer_email: str
    step: str
    explanation_step: int  # 0-4: which section is currently being discussed


def _find_email(text: str) -> str | None:
    m = EMAIL_RE.search(text)
    return m.group(0) if m else None


UNDERSTOOD_KEYWORDS = [
    "yes", "yeah", "yep", "ok", "okay", "sure", "alright",
    "understand", "understood", "got it", "clear", "i get it",
    "paham", "mengerti", "oke", "sudah", "ngerti",
]

def _is_understood(text: str) -> bool:
    """Check if customer confirmed they understand using keyword matching."""
    text_lower = text.lower().strip()
    return any(kw in text_lower for kw in UNDERSTOOD_KEYWORDS)


def _friendly_section_explanation(section_index: int) -> str:
    """Ask LLM to explain a section in a friendly, conversational way."""
    title, content = SECTIONS[section_index]
    total = len(SECTIONS)
    result = llm.invoke([
        SystemMessage(
            f"You are a warm and friendly insurance assistant. "
            f"Explain the '{title}' section of an insurance product to a customer "
            f"in a simple, conversational, easy-to-understand way — like talking to a friend. "
            f"Avoid jargon. Keep it concise. "
            f"This is section {section_index + 1} of {total}. "
            f"End your explanation by asking if they understand, and tell them to type **'Yes'** if they do so we can move on to the next part."
        ),
        HumanMessage(content),
    ])
    return result.content


def _router(state: AgentState) -> str:
    step = state.get("step", "collect_agent_email")
    return END if step == "done" else step


# --- Nodes ---

def collect_agent_email(state: AgentState) -> dict:
    email = _find_email(state["messages"][-1].content)
    if email:
        return {
            "agent_email": email,
            "step": "collect_customer_email",
            "messages": [AIMessage(
                f"Got it! Agent email recorded: **{email}** ✅\n\n"
                "Now, could you please share your (the customer's) email address?"
            )],
        }
    return {"messages": [AIMessage(
        "Hmm, I couldn't find a valid email there. "
        "Could you please provide the agent's email? (e.g. agent@company.com)"
    )]}


def collect_customer_email(state: AgentState) -> dict:
    email = _find_email(state["messages"][-1].content)
    if email:
        explanation = _friendly_section_explanation(0)
        title = SECTIONS[0][0]
        return {
            "customer_email": email,
            "step": "explain_section",
            "explanation_step": 0,
            "messages": [AIMessage(
                f"Perfect! Your email has been recorded: **{email}** 😊\n\n"
                f"Let's get started! I'll walk you through the product step by step. "
                f"There are **{len(SECTIONS)} sections** in total — I'll explain one at a time, "
                f"and just let me know when you understand each part before we move on.\n\n"
                f"**Section 1: {title}**\n\n"
                f"{explanation}"
            )],
        }
    return {"messages": [AIMessage(
        "I couldn't find a valid email. "
        "Could you share your email address? (e.g. customer@email.com)"
    )]}


def explain_section(state: AgentState) -> dict:
    last_msg = state["messages"][-1].content
    current_step = state.get("explanation_step", 0)
    title, content = SECTIONS[current_step]

    if _is_understood(last_msg):
        next_step = current_step + 1

        # All sections done → confirm and send emails
        if next_step >= len(SECTIONS):
            return {"step": "send_confirmation"}

        # Explain next section
        next_title, _ = SECTIONS[next_step]
        explanation = _friendly_section_explanation(next_step)
        return {
            "explanation_step": next_step,
            "messages": [AIMessage(
                f"Great, moving on! 🎉\n\n"
                f"**Section {next_step + 1}: {next_title}**\n\n"
                f"{explanation}"
            )],
        }

    # Customer has a question — answer based on current section
    # Include supporting docs context only if they ask about it
    asks_for_docs = any(
        kw in last_msg.lower()
        for kw in ["document", "dokumen", "supporting", "required", "what do i need", "apa yang dibutuhkan"]
    )
    extra = f"\n\nSupporting documents info (only use if relevant):\n{SUPPORTING_DOCS}" if asks_for_docs else ""

    response = llm.invoke([
        SystemMessage(
            f"You are a warm, friendly insurance assistant. "
            f"The customer is currently on the '{title}' section. "
            f"Answer their question based ONLY on this section's content:\n\n{content}{extra}\n\n"
            f"Be simple, friendly, and reassuring. "
            f"After answering, gently ask if that clears things up, and remind them to type **'Yes'** when they're ready to continue. 😊"
        ),
        *state["messages"],
    ])
    return {
        "explanation_step": current_step,
        "messages": [response],
    }


def send_confirmation(state: AgentState) -> dict:
    from email_service import send_confirmation_emails
    try:
        send_confirmation_emails(state["agent_email"], state["customer_email"])
        msg = (
            "Wonderful! You've gone through all sections of the product — great job! 🎉\n\n"
            "Confirmation emails have been sent to both you and the agent.\n\n"
            "**Summary:** You have confirmed that you understand the insurance product "
            "based on the original product specifications and agree to proceed with payment.\n\n"
            "Your agent will be in touch shortly to finalize everything. Thank you! 😊"
        )
    except Exception as e:
        msg = (
            "Wonderful! You've gone through all sections of the product — great job! 🎉\n\n"
            "You have confirmed that you understand the insurance product and agree to proceed with payment.\n\n"
            f"Note: There was a small issue sending the confirmation email ({e}). "
            "Please inform your agent directly."
        )
    return {"step": "done", "messages": [AIMessage(msg)]}


# --- Conditional edges ---

def _after_explain(state: AgentState) -> str:
    return "send_confirmation" if state.get("step") == "send_confirmation" else END


# --- Build graph ---

def create_graph():
    g = StateGraph(AgentState)

    g.add_node("collect_agent_email", collect_agent_email)
    g.add_node("collect_customer_email", collect_customer_email)
    g.add_node("explain_section", explain_section)
    g.add_node("send_confirmation", send_confirmation)

    g.add_conditional_edges(START, _router, {
        "collect_agent_email": "collect_agent_email",
        "collect_customer_email": "collect_customer_email",
        "explain_section": "explain_section",
        "send_confirmation": "send_confirmation",
        END: END,
    })

    g.add_edge("collect_agent_email", END)
    g.add_edge("collect_customer_email", END)
    g.add_conditional_edges("explain_section", _after_explain, {
        "send_confirmation": "send_confirmation",
        END: END,
    })
    g.add_edge("send_confirmation", END)

    return g.compile(checkpointer=MemorySaver())


graph = create_graph()
