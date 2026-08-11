"""Streamlit user interface for LexAssist."""

from __future__ import annotations

import base64
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
        [data-testid="stChatMessage"] {{
            align-items: flex-end;
            background: transparent !important;
            border: 0 !important;
            gap: 0 !important;
            padding: .35rem 0 !important;
        }}
        [data-testid="stChatMessageAvatarUser"],
        [data-testid="stChatMessageAvatarAssistant"] {{
            display: none !important;
        }}
        [data-testid="stChatMessageContent"] {{
            width: fit-content;
            max-width: min(72%, 720px);
            padding: .75rem 1rem;
            background: rgba(9, 38, 63, .94);
            border: 1px solid rgba(112, 195, 255, .24);
            border-radius: 4px 18px 18px 18px;
            box-shadow: 0 4px 14px rgba(0, 0, 0, .18);
        }}
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{
            justify-content: flex-end;
        }}
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])
        [data-testid="stChatMessageContent"] {{
            background: #0b6d5a;
            border: 0;
            border-radius: 18px 4px 18px 18px;
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
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

question = st.chat_input("For example: What should I check before signing a rental agreement?")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
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
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
