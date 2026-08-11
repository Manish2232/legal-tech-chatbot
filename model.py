"""Reusable AI core for LexAssist.

The module can power the Streamlit app or run as a small terminal chatbot.
Set MISTRAL_API_KEY in a .env file before starting the application.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_mistralai import ChatMistralAI

from database import get_messages, save_message

load_dotenv()

DEFAULT_MODEL = "mistral-small-2506"
MAX_HISTORY_MESSAGES = 16
MAX_QUESTION_LENGTH = 4_000
DISCLAIMER = (
    "This is general legal information, not legal advice. "
    "Consider consulting a qualified lawyer in your jurisdiction."
)


class LexAssistConfigurationError(RuntimeError):
    """Raised when LexAssist is missing required configuration."""


SYSTEM_PROMPT = f"""
You are LexAssist, an AI legal-information assistant. Your role is to help people
understand legal topics in clear, professional, plain language.

Rules:
- Give general legal information only; never claim to be a lawyer or create an
  attorney-client relationship.
- Do not invent laws, case citations, deadlines, government agencies, or facts.
  Say when information is uncertain or may have changed.
- Jurisdiction can change the answer. Ask for country/state only when it is
  material and missing; otherwise give a useful high-level answer first.
- Do not promise a legal outcome. Explain relevant factors, practical options,
  and reasonable next steps.
- For imminent danger, criminal accusations, eviction, detention, abuse, or a
  fast-approaching legal deadline, encourage prompt help from a local qualified
  lawyer or relevant emergency/local support service.
- Use the previous conversation only when relevant. Respect the user's privacy;
  do not request sensitive personal information unless essential.

Response format:
1. Give a direct answer in 1-3 short paragraphs.
2. Use a short "Key factors" list when it adds clarity.
3. End every response with exactly this sentence:
"{DISCLAIMER}"
"""


prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ]
)

_sessions: dict[str, InMemoryChatMessageHistory] = {}


def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    """Load a saved conversation into a short-lived LangChain history object."""
    if not session_id.strip():
        raise ValueError("A non-empty session ID is required.")
    if session_id not in _sessions:
        history = InMemoryChatMessageHistory()
        for message in get_messages(session_id):
            if message["role"] == "user":
                history.add_user_message(message["content"])
            else:
                history.add_ai_message(message["content"])
        _sessions[session_id] = history
    return _sessions[session_id]


def clear_session_history(session_id: str) -> None:
    """Discard cached context; saved chat history remains available in SQLite."""
    _sessions.pop(session_id, None)


def _trim_history(session_id: str) -> None:
    """Keep context useful and avoid unbounded token/cost growth."""
    history = get_session_history(session_id)
    if len(history.messages) > MAX_HISTORY_MESSAGES:
        latest_messages = history.messages[-MAX_HISTORY_MESSAGES:]
        history.clear()
        history.add_messages(latest_messages)


@lru_cache(maxsize=1)
def get_chatbot() -> RunnableWithMessageHistory:
    """Create and cache the configured Mistral conversation chain."""
    if not os.getenv("MISTRAL_API_KEY"):
        raise LexAssistConfigurationError(
            "MISTRAL_API_KEY is missing. Add it to your .env file before starting LexAssist."
        )

    model = ChatMistralAI(
        model=os.getenv("LEXASSIST_MODEL", DEFAULT_MODEL),
        temperature=0.2,
        max_retries=2,
        timeout=30,
    )
    return RunnableWithMessageHistory(
        prompt | model,
        get_session_history,
        input_messages_key="question",
        history_messages_key="history",
    )


def ask(question: str, session_id: str) -> str:
    """Validate a question, retain bounded history, and return the assistant reply."""
    question = question.strip()
    if not question:
        raise ValueError("Please enter a legal question.")
    if len(question) > MAX_QUESTION_LENGTH:
        raise ValueError(f"Please keep questions under {MAX_QUESTION_LENGTH:,} characters.")

    _trim_history(session_id)
    response = get_chatbot().invoke(
        {"question": question},
        config={"configurable": {"session_id": session_id}},
    )
    answer = str(response.content)
    save_message(session_id, "user", question)
    save_message(session_id, "assistant", answer)
    return answer


def main() -> None:
    """Run LexAssist in a terminal for quick local testing."""
    session_id = "terminal-user"
    print("LexAssist — general legal information assistant")
    print("Type 'exit' to end the conversation.\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nChat ended.")
            return

        if question.lower() in {"exit", "quit"}:
            print("Chat ended.")
            return

        try:
            print(f"\nLexAssist: {ask(question, session_id)}\n")
        except (LexAssistConfigurationError, ValueError) as error:
            print(f"\n{error}\n")
        except Exception:
            print("\nLexAssist could not reach the AI service. Please try again shortly.\n")


if __name__ == "__main__":
    main()
