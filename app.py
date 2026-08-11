"""Streamlit user interface for LexAssist."""

from __future__ import annotations

import base64
import html
from pathlib import Path
from uuid import uuid4

import streamlit as st

from database import get_messages, initialize_database, list_conversations
from model import LexAssistConfigurationError, ask, clear_session_history


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
    st.session_state.messages.append({"role": "assistant", "content": answer})
