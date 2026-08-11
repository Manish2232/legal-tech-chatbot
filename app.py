"""Streamlit user interface for LexAssist."""

from __future__ import annotations

import base64
import html
from pathlib import Path
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from database import (
    get_messages,
    initialize_database,
    list_conversations,
    update_assistant_message,
)
from model import LexAssistConfigurationError, ask, clear_session_history
from pdf_utils import create_answer_pdf


st.set_page_config(page_title="LexAssist | Legal Information", page_icon="⚖️", layout="wide")
initialize_database()

BASE_DIR = Path(__file__).parent
background_path = BASE_DIR / "wallpaper.png"
background_css = ""
if background_path.exists():
    background_b64 = base64.b64encode(background_path.read_bytes()).decode()
    background_css = f"""
        background: linear-gradient(rgba(4, 10, 20, 0.80), rgba(4, 10, 20, 0.90)),
                    url('data:image/png;base64,{background_b64}');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    """

st.markdown(
    f"""
    <style>
        .stApp {{ {background_css} background-color: #07111f; }}
        [data-testid="stHeader"] {{ background: transparent; }}
        [data-testid="stSidebar"] {{ background: rgba(5, 15, 29, .93); }}
        .chat-row {{
            display: flex;
            width: 100%;
            margin: 1rem 0;
        }}
        .chat-row.user {{
            justify-content: flex-end;
        }}
        .chat-row.assistant {{
            justify-content: flex-start;
        }}
        .chat-text {{
            max-width: 68%;
            padding: .15rem .8rem;
            background: transparent;
            border: 0;
            box-shadow: none;
            font-size: 1.04rem;
            line-height: 1.65;
            overflow-wrap: anywhere;
        }}
        .chat-row.user .chat-text {{
            color: #b9fff0;
            text-align: right;
        }}
        .chat-row.assistant .chat-text {{
            width: 100%;
            max-width: 100%;
            color: #f2f8ff;
            text-align: left;
        }}
        .credit-box {{
            margin: .35rem 0 1.4rem;
            padding: 1rem .8rem;
            border: 1px solid #53e6ff;
            border-radius: 12px;
            background: rgba(5, 25, 43, .82);
            box-shadow: 0 0 7px #53e6ff, 0 0 18px rgba(83, 230, 255, .85),
                        inset 0 0 12px rgba(83, 230, 255, .18);
            color: #edfcff;
            font-weight: 600;
            line-height: 1.55;
            text-align: center;
            text-shadow: 0 0 7px rgba(83, 230, 255, .9);
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid4())


def render_message(role: str, content: str) -> None:
    """Render a compact, borderless left/right chat message."""
    safe_content = html.escape(content).replace("\n", "<br>")
    st.markdown(
        f'<div class="chat-row {role}"><div class="chat-text">{safe_content}</div></div>',
        unsafe_allow_html=True,
    )


def render_copy_button(content: str, message_id: int | None) -> None:
    """Render a browser-side copy icon without sending text to the server."""
    encoded_text = base64.b64encode(content.encode("utf-8")).decode("ascii")
    button_id = f"copy-{message_id or 'current'}"
    components.html(
        f"""
        <style>
            body {{ margin: 0; background: transparent; }}
            button {{
                cursor: pointer; border: 0; border-radius: 6px; background: transparent;
                color: #a9c2d8; font-size: 18px; padding: 3px 7px;
            }}
            button:hover {{ background: rgba(92, 184, 255, .16); color: #ffffff; }}
        </style>
        <button id="{button_id}" title="Copy answer" aria-label="Copy answer">⧉</button>
        <script>
            document.getElementById("{button_id}").addEventListener("click", async () => {{
                await navigator.clipboard.writeText(atob("{encoded_text}"));
            }});
        </script>
        """,
        height=32,
    )


def render_answer_actions(message: dict[str, str | int]) -> None:
    """Show copy, PDF download, and edit controls under a saved answer."""
    content = str(message["content"])
    message_id = message.get("id")
    action_key = str(message_id) if message_id is not None else "current"
    action_columns = st.columns([0.06, 0.07, 0.87])
    with action_columns[0]:
        render_copy_button(content, int(message_id) if message_id is not None else None)
    with action_columns[1]:
        with st.popover("⋮", help="Answer options"):
            st.download_button(
                "Download as PDF",
                data=create_answer_pdf(content),
                file_name="lexassist-answer.pdf",
                mime="application/pdf",
                key=f"download-answer-{action_key}",
                use_container_width=True,
            )
            if message_id is not None:
                edited_content = st.text_area(
                    "Edit answer",
                    value=content,
                    key=f"edit-answer-{message_id}",
                    height=160,
                )
                if st.button("Save changes", key=f"save-answer-{message_id}"):
                    update_assistant_message(
                        st.session_state.session_id,
                        int(message_id),
                        edited_content,
                    )
                    clear_session_history(st.session_state.session_id)
                    st.session_state.messages = get_messages(st.session_state.session_id)
                    st.rerun()

with st.sidebar:
    st.markdown(
        """
        <div class="credit-box">
            All Credit goes to<br>
            Shrila Prabhupada ji<br>
            and Guru maharaj HH BPBS
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.title("LexAssist")
    st.caption("Legal information, explained clearly.")
    if st.button("Start a new chat", use_container_width=True):
        clear_session_history(st.session_state.session_id)
        st.session_state.messages = []
        st.session_state.session_id = str(uuid4())
        st.rerun()
    st.divider()
    st.subheader("Previous chats")
    conversations = list_conversations()
    if not conversations:
        st.caption("Your saved chats will appear here.")
    else:
        for conversation in conversations:
            is_active = conversation["session_id"] == st.session_state.session_id
            label = f"• {conversation['title']}" if is_active else conversation["title"]
            if st.button(
                label,
                key=f"conversation-{conversation['session_id']}",
                use_container_width=True,
            ):
                clear_session_history(st.session_state.session_id)
                st.session_state.session_id = conversation["session_id"]
                st.session_state.messages = get_messages(conversation["session_id"])
                st.rerun()
    st.divider()
    st.subheader("Before you begin")
    st.caption("LexAssist provides general information, not legal advice. Laws vary by location.")

st.title("⚖️ LexAssist")
st.caption("Ask about a legal topic in plain language. Include your country or state when it matters.")

for message in st.session_state.messages:
    render_message(message["role"], message["content"])
    if message["role"] == "assistant":
        render_answer_actions(message)

question = st.chat_input("For example: What should I check before signing a rental agreement?")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    render_message("user", question)

    with st.spinner("Reviewing your question…"):
        try:
            answer = ask(question, st.session_state.session_id)
        except LexAssistConfigurationError as error:
            answer = str(error)
        except ValueError as error:
            answer = str(error)
        except Exception:
            answer = (
                "I couldn't reach the AI service just now. Please check your connection "
                "and try again in a moment."
            )
    render_message("assistant", answer)
    st.session_state.messages = get_messages(st.session_state.session_id)
    render_answer_actions(st.session_state.messages[-1])
