import base64
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

load_dotenv()

# ---------------------------------------------------------------------------
# Original chatbot logic (unchanged)
# ---------------------------------------------------------------------------

model = ChatMistralAI(
    model="mistral-small-2506",
    temperature=0.7
)

prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are LexAssist, an AI legal-information assistant.

Provide clear, professional, plain-language legal information.
You are not a lawyer and do not provide legal advice or create an attorney-client relationship.
Use the earlier conversation when it is relevant.
If the jurisdiction is missing and necessary, ask for it.
End relevant answers with:
"This is general legal information, not legal advice. Consider consulting a qualified lawyer in your jurisdiction."
"""),

    # Previous user/assistant messages will appear here
    MessagesPlaceholder(variable_name="history"),

    ("human", "{question}")
])

chain = prompt | model

# Stores chat history in memory for each session ID
chat_sessions = {}

def get_session_history(session_id: str):
    if session_id not in chat_sessions:
        chat_sessions[session_id] = InMemoryChatMessageHistory()
    return chat_sessions[session_id]

chatbot = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="question",
    history_messages_key="history"
)

session_id = "user_001"  # Use a unique ID per logged-in user

# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="LexAssist", page_icon="⚖️", layout="wide")

BASE_DIR = Path(__file__).parent
bg_b64 = base64.b64encode((BASE_DIR / "wallpaper.png").read_bytes()).decode()

st.markdown(f"""
<style>

/* ---------- Background ---------- */
.stApp {{
    background: linear-gradient(rgba(0,0,0,0.35), rgba(0,0,0,0.55)),
                url("data:image/png;base64,{bg_b64}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}

/* ---------- Transparent header ---------- */
[data-testid="stHeader"] {{
    background: rgba(0,0,0,0);
}}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {{
    background: rgba(8, 10, 14, 0.82);
    border-right: 1px solid rgba(90, 200, 255, 0.25);
}}

/* ---------- Neon glowing credit box ---------- */
.neon-credit-box {{
    border: 1px solid #4fd8ff;
    border-radius: 12px;
    padding: 16px 14px;
    margin-bottom: 22px;
    text-align: center;
    background: rgba(10, 14, 20, 0.6);
    box-shadow:
        0 0 6px #4fd8ff,
        0 0 14px #4fd8ff,
        0 0 24px rgba(79, 216, 255, 0.6),
        inset 0 0 10px rgba(79, 216, 255, 0.35);
}}
.neon-credit-box p {{
    margin: 0;
    color: #eafcff;
    font-size: 15px;
    font-weight: 600;
    line-height: 1.5;
    text-shadow:
        0 0 4px #4fd8ff,
        0 0 10px #4fd8ff,
        0 0 18px rgba(79, 216, 255, 0.8);
    letter-spacing: 0.3px;
}}

/* ---------- History section ---------- */
.history-heading {{
    color: #cfefff;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    opacity: 0.75;
    margin: 6px 0 10px 0;
}}
.history-item {{
    background: rgba(255, 255, 255, 0.04);
    border-left: 2px solid #4fd8ff;
    border-radius: 4px;
    padding: 8px 10px;
    margin-bottom: 8px;
    color: #e6f7ff;
    font-size: 13px;
    line-height: 1.4;
    word-wrap: break-word;
}}

/* ---------- Chat area readability ---------- */
[data-testid="stChatMessage"] {{
    background: rgba(8, 10, 14, 0.72);
    border-radius: 12px;
    border: 1px solid rgba(79, 216, 255, 0.18);
}}

h1, h2, h3, p, span, label {{
    color: #f2fbff;
}}

</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar: neon credit box (top) + chat history
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("""
    <div class="neon-credit-box">
        <p>All credit goes to<br>Shrila Prabhupada ji<br>and<br>H.H BPBS Maharaj ji</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="history-heading">Chat History</div>', unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if not st.session_state.messages:
        st.markdown('<div class="history-item">No messages yet.</div>', unsafe_allow_html=True)
    else:
        for msg in st.session_state.messages:
            role_label = "You" if msg["role"] == "user" else "LexAssist"
            st.markdown(
                f'<div class="history-item"><b>{role_label}:</b> {msg["content"]}</div>',
                unsafe_allow_html=True
            )

# ---------------------------------------------------------------------------
# Main chat interface
# ---------------------------------------------------------------------------

st.title("⚖️ LexAssist")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

question = st.chat_input("Ask your legal question...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    response = chatbot.invoke(
        {"question": question},
        config={"configurable": {"session_id": session_id}}
    )

    st.session_state.messages.append({"role": "assistant", "content": response.content})
    with st.chat_message("assistant"):
        st.markdown(response.content)
