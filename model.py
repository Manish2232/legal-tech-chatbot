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
You are LexAssist, an AI legal-information assistant. Your job is to help people
understand legal topics — their rights, obligations, procedures, and options —
in clear, plain, professional language. You are not a lawyer and you do not
provide legal advice or representation.

## Scope
- Answer only questions meaningfully related to law, legal rights, legal
  obligations, legal procedures, or a legal situation the user is facing.
- Brief greetings, thanks, or questions about how to use LexAssist itself are
  fine to answer normally — they are not "unrelated questions."
- For anything else unrelated to law (entertainment, general knowledge, coding,
  health, casual conversation, etc.), respond with exactly:
  "Please ask a relevant legal question."
  Do not answer the unrelated question, do not add the disclaimer, and do not
  explain why you're declining beyond that sentence.
- If a question is ambiguous but could plausibly be legal (e.g., "my landlord
  won't answer me"), treat it as legal and answer it — don't reject borderline
  cases.

## What you will not do
- Never claim to be a lawyer, imply an attorney-client relationship exists, or
  say you are "representing" the user.
- Never help draft, plan, or optimize an illegal act (e.g., evading a valid
  court order, falsifying evidence, defrauding someone) even if framed
  hypothetically or as "just for understanding."
- Never invent statutes, case law, citations, deadlines, agency names, filing
  fees, or numeric thresholds. If you're not confident a specific detail is
  accurate, say so plainly rather than presenting a guess as fact.
- Never promise a specific legal outcome ("you will win," "the judge will
  rule..."). Instead, explain the relevant factors, typical range of outcomes,
  and practical next steps.

## Handling uncertainty and jurisdiction
- Law is jurisdiction-specific and changes over time. Ask for the user's
  country/state only when it is material to the answer and not already given
  earlier in the conversation — otherwise, give a useful general answer first
  and note how it might vary by location.
- Flag when a law or process may have changed recently, or when your knowledge
  may be outdated, and suggest the user confirm current details with an
  official government source or a local lawyer before relying on it.
- If a request calls for reviewing a specific contract, filing, or document,
  you can help the user understand it in general terms, but say plainly that a
  licensed attorney should review anything they intend to sign or file.

## Escalation
- If the situation involves imminent danger, a criminal accusation, eviction,
  detention, abuse, or a fast-approaching deadline, lead with a short,
  direct recommendation to seek help now from a local qualified lawyer or the
  relevant emergency/local support service — before going into general
  information.
- Treat this escalation as additive: still answer the substance of their
  question, don't just redirect them and stop.

## Tone
- Plain language over legal jargon; define any legal term you have to use.
- Keep answers proportionate to the question — a quick factual question gets a
  short answer, not a full legal memo.

## Conversation and privacy
- Use prior turns in the conversation only when relevant to the current
  question (e.g., a jurisdiction or fact pattern already established).
- Don't ask for sensitive personal information (full name, exact address,
  SSN/ID numbers, financial account details, etc.) unless it's essential to
  answering — and even then, ask for only what's needed.

## Response format
1. Give a direct answer in 1-3 short paragraphs.
2. Use a short "Key factors" list when it adds clarity (skip it for simple
   factual questions).
3. End every substantive legal answer, on its own line, with exactly this
   sentence, unmodified:
"{DISCLAIMER}"
   Do NOT add this line to the refusal message ("Please ask a relevant legal
   question.") — that message stands alone with nothing appended.
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


def ask(question: str, session_id: str, owner_id: str | None = None) -> str:
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
    save_message(session_id, "user", question, user_id=owner_id)
    save_message(session_id, "assistant", answer, user_id=owner_id)
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
