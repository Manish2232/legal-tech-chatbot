"""Streamlit user interface for LexAssist."""

from __future__ import annotations

import base64
import html
from pathlib import Path
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from database import (
    authenticate_user,
    delete_conversation,
    get_messages,
    initialize_database,
    list_conversations,
    register_user,
    request_password_reset,
    resend_verification_code,
    reset_password,
    update_assistant_message,
    verify_email,
)
from model import LexAssistConfigurationError, ask, clear_session_history
from pdf_utils import create_answer_pdf, create_chat_report_pdf
from logo_assets import LOGO_SIDEBAR_B64


st.set_page_config(page_title="LexAssist | Legal Information", page_icon="⚖️", layout="wide")
initialize_database()

if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid4())
if "pending_verification_email" not in st.session_state:
    st.session_state.pending_verification_email = None


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
                color: #8fa8c2; font-size: 15px; line-height: 1; padding: 2px 4px;
                transition: all .15s ease;
            }}
            button:hover {{ background: rgba(92, 184, 255, .18); color: #ffffff; }}
        </style>
        <button id="{button_id}" title="Copy answer" aria-label="Copy answer">⧉</button>
        <script>
            document.getElementById("{button_id}").addEventListener("click", async () => {{
                const button = document.getElementById("{button_id}");
                const originalIcon = button.textContent;
                try {{
                    await navigator.clipboard.writeText(atob("{encoded_text}"));
                    button.textContent = "✓";
                    setTimeout(() => {{ button.textContent = originalIcon; }}, 2500);
                }} catch (error) {{
                    button.textContent = "!";
                    setTimeout(() => {{ button.textContent = originalIcon; }}, 2500);
                }}
            }});
        </script>
        """,
        height=26,
    )


def render_answer_actions(message: dict[str, str | int]) -> None:
    """Show copy, PDF download, and edit controls under a saved answer."""
    content = str(message["content"])
    message_id = message.get("id")
    action_key = str(message_id) if message_id is not None else "current"
    action_columns = st.columns([0.025, 0.03, 0.945], gap="small")
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


def render_user_copy_action(message: dict[str, str | int]) -> None:
    """Show the copy control below a user message, aligned to the right."""
    message_id = message.get("id")
    action_columns = st.columns([0.97, 0.03], gap="small")
    with action_columns[1]:
        render_copy_button(
            str(message["content"]),
            int(message_id) if message_id is not None else None,
        )


def show_auth_screen() -> None:
    """Display professional login and signup screens before chat access."""
    BASE_DIR = Path(__file__).parent
    background_path = BASE_DIR / "wallpaper.png"
    background_css = ""
    if background_path.exists():
        background_b64 = base64.b64encode(background_path.read_bytes()).decode()
        background_css = f"""
            background: linear-gradient(rgba(4, 10, 20, 0.86), rgba(4, 10, 20, 0.94)),
                        url('data:image/png;base64,{background_b64}');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        """

    st.markdown(
        f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Lora:ital@0;1&family=Orbitron:wght@600;700;800;900&display=swap');
            .stApp {{ {background_css} background-color: #070f1c; }}
            .auth-shell {{
                max-width: 560px; margin: 4rem auto 0; padding: 2rem; background: rgba(12, 19, 31, 0.9);
                border: 1px solid rgba(83, 230, 255, 0.2); border-radius: 18px; box-shadow: 0 18px 40px rgba(0,0,0,.3);
            }}
            .auth-title {{ font-size: 2.2rem; font-weight: 700; color: #edfaff; margin-bottom: .5rem; }}
            .auth-subtitle {{ color: #8ea9c3; margin-bottom: 1.5rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="auth-shell"><div class="auth-title">LexAssist</div><div class="auth-subtitle">Professional legal guidance with secure, personalized access.</div></div>',
        unsafe_allow_html=True,
    )

    tab_login, tab_signup = st.tabs(["Log in", "Create account"])

    with tab_login:
        st.subheader("Welcome back")
        email = st.text_input("Email", key="auth_login_email")
        password = st.text_input("Password", type="password", key="auth_login_password")
        if st.button("Login"):
            try:
                user = authenticate_user(email, password)
                if user is None:
                    st.error("Invalid email or password.")
                else:
                    st.session_state.user = user
                    st.session_state.messages = []
                    st.session_state.session_id = str(uuid4())
                    st.rerun()
            except ValueError as error:
                st.error(str(error))

        if st.button("Forgot password?"):
            st.session_state.show_password_reset = True
            st.session_state.reset_email = email or ""
            st.rerun()

        if st.session_state.get("show_password_reset"):
            st.divider()
            st.subheader("Reset your password")
            reset_email = st.text_input("Email address", value=st.session_state.get("reset_email", ""), key="reset_email_input")
            reset_code = st.text_input("Reset code", key="reset_code_input")
            new_password = st.text_input("New password", type="password", key="reset_new_password")
            confirm_new_password = st.text_input("Confirm new password", type="password", key="reset_confirm_password")
            if st.button("Send reset code"):
                try:
                    result = request_password_reset(reset_email)
                    if result["email_sent"]:
                        st.success("A reset code has been sent to your email.")
                    else:
                        st.info(f"Development reset code: {result['reset_code']}")
                except ValueError as error:
                    st.error(str(error))
            if st.button("Set new password"):
                if new_password != confirm_new_password:
                    st.error("Passwords do not match.")
                else:
                    try:
                        reset_password(reset_email, reset_code, new_password)
                        st.success("Your password has been reset successfully. You can now log in.")
                        st.session_state.show_password_reset = False
                        st.session_state.reset_email = ""
                        st.rerun()
                    except ValueError as error:
                        st.error(str(error))

    with tab_signup:
        st.subheader("Create your account")
        name = st.text_input("Full name", key="auth_signup_name")
        email = st.text_input("Email address", key="auth_signup_email")
        password = st.text_input("Password", type="password", key="auth_signup_password")
        confirm_password = st.text_input("Confirm password", type="password", key="auth_signup_confirm")
        if st.button("Sign up"):
            if password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    result = register_user(name, email, password)
                    st.session_state.pending_verification_email = result["email"]
                    st.session_state.pending_verification_code = result.get("verification_code")
                    st.success(
                        "Account created. Check your email for a verification code."
                        if result["email_sent"]
                        else "Account created. Use the verification code below to continue."
                    )
                    if result.get("verification_code"):
                        st.info(f"Development verification code: {result['verification_code']}")
                except ValueError as error:
                    st.error(str(error))

    if st.session_state.pending_verification_email:
        st.divider()
        st.subheader("Verify your email")
        code = st.text_input("Verification code", key="email_verification_code")
        if st.button("Verify email"):
            try:
                user = verify_email(st.session_state.pending_verification_email, code)
                st.session_state.user = user
                st.session_state.pending_verification_email = None
                st.session_state.pending_verification_code = None
                st.session_state.messages = []
                st.session_state.session_id = str(uuid4())
                st.success("Email verified successfully. You are now logged in.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))
        if st.button("Resend code"):
            try:
                result = resend_verification_code(st.session_state.pending_verification_email)
                if result["email_sent"]:
                    st.success("A fresh verification code has been sent.")
                else:
                    st.info(f"Development verification code: {result['verification_code']}")
            except ValueError as error:
                st.error(str(error))


BASE_DIR = Path(__file__).parent
background_path = BASE_DIR / "wallpaper.png"
background_css = ""
if background_path.exists():
    background_b64 = base64.b64encode(background_path.read_bytes()).decode()
    background_css = f"""
        background: linear-gradient(rgba(4, 10, 20, 0.86), rgba(4, 10, 20, 0.94)),
                    url('data:image/png;base64,{background_b64}');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    """

st.markdown(
    f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Lora:ital@0;1&family=Orbitron:wght@600;700;800;900&display=swap');
        html, body, [class*="css"] {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }}
        .stApp {{ {background_css} background-color: #070f1c; }}
        [data-testid="stHeader"] {{ background: transparent; }}
        [data-testid="stSidebar"] {{ background: linear-gradient(180deg, rgba(6, 16, 30, .97) 0%, rgba(4, 11, 21, .97) 100%); border-right: 1px solid rgba(83, 230, 255, .12); }}
        .lexassist-brand-title {{ font-family: 'Inter', sans-serif; font-weight: 700; letter-spacing: .3px; background: linear-gradient(90deg, #ffffff 0%, #9beaff 45%, #53c8ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; filter: drop-shadow(0 0 6px rgba(83, 230, 255, .35)); margin: 0; line-height: 1.2; }}
        .lexassist-brand-title.main {{ font-size: 1.9rem; }}
        .lexassist-logo-img-sidebar {{ display: block; margin: 0 auto .3rem; max-width: 220px; width: 100%; height: auto; }}
        [data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] p {{ color: #8fa8c2; }}
        [data-testid="stSidebar"] h3 {{ color: #dceeff; font-size: .92rem; text-transform: uppercase; letter-spacing: .8px; font-weight: 600; opacity: .85; }}
        [data-testid="stSidebar"] hr {{ border-color: rgba(83, 230, 255, .12); margin: 1.1rem 0; }}
        [data-testid="stSidebar"] .stButton > button {{ background: rgba(15, 32, 52, .65); border: 1px solid rgba(83, 230, 255, .18); color: #e6f4ff; border-radius: 10px; font-weight: 500; text-align: left; transition: all .18s ease; }}
        [data-testid="stSidebar"] .stButton > button:hover {{ background: rgba(83, 230, 255, .12); border-color: rgba(83, 230, 255, .5); color: #ffffff; transform: translateX(1px); }}
        [data-testid="stSidebar"] .stButton > button:first-child {{ background: linear-gradient(90deg, rgba(83,230,255,.18), rgba(185,255,240,.12)); border-color: rgba(83, 230, 255, .55); font-weight: 600; }}
        .stApp > header + div .stCaption {{ color: #90a9c4; }}
        .chat-row {{ display: flex; width: 100%; margin: .55rem 0; animation: fadeIn .25s ease-out; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        .chat-row.user {{ justify-content: flex-end; }}
        .chat-row.assistant {{ justify-content: flex-start; }}
        .chat-text {{ font-size: 1.3rem; line-height: 1.85; overflow-wrap: anywhere; }}
        .chat-row.user .chat-text {{ max-width: 68%; padding: .15rem .8rem; background: transparent; border: 0; box-shadow: none; color: #b9fff0; text-align: right; }}
        .chat-row.assistant .chat-text {{ width: 100%; max-width: 100%; padding: .15rem .8rem; background: transparent; border: 0; box-shadow: none; color: #f2f8ff; text-align: left; }}
        [data-testid="stHorizontalBlock"] {{ align-items: center !important; }}
        [data-testid="stHorizontalBlock"] [data-testid="stColumn"] {{ display: flex !important; align-items: center !important; justify-content: center !important; }}
        [data-testid="stHorizontalBlock"] [data-testid="stColumn"] [data-testid="stElementContainer"], [data-testid="stHorizontalBlock"] [data-testid="stColumn"] [data-testid="element-container"] {{ margin: 0 !important; }}
        [data-testid="stHorizontalBlock"] iframe {{ display: block !important; }}
        [data-testid="stPopover"] {{ display: flex !important; align-items: center !important; }}
        [data-testid="stPopover"] > button, [data-testid="stPopover"] button {{ min-width: 26px !important; min-height: 26px !important; width: 26px !important; height: 26px !important; padding: 0 !important; margin: 0 !important; background: transparent !important; background-color: transparent !important; border: none !important; border-radius: 50% !important; box-shadow: none !important; color: #8fa8c2 !important; font-size: 15px !important; line-height: 1 !important; transition: all .15s ease !important; }}
        [data-testid="stPopover"] > button:hover, [data-testid="stPopover"] button:hover {{ background: rgba(92, 184, 255, .18) !important; color: #ffffff !important; }}
        [data-testid="stPopover"] > button svg, [data-testid="stPopover"] button svg {{ display: none !important; }}
        [data-testid="stPopoverBody"] {{ background: rgba(9, 19, 33, .98) !important; border: 1px solid rgba(83, 230, 255, .18) !important; border-radius: 12px !important; box-shadow: 0 8px 28px rgba(0, 0, 0, .45) !important; }}
        .stDownloadButton > button, div[data-testid="stPopoverBody"] .stButton > button {{ background: rgba(83, 230, 255, .1); border: 1px solid rgba(83, 230, 255, .3); color: #eafcff; border-radius: 8px; font-weight: 500; transition: all .15s ease; }}
        .stDownloadButton > button:hover, div[data-testid="stPopoverBody"] .stButton > button:hover {{ background: rgba(83, 230, 255, .22); border-color: rgba(83, 230, 255, .55); }}
        [data-testid="stChatInput"] {{ border: 1px solid rgba(83, 230, 255, .25) !important; background: rgba(9, 19, 33, .9) !important; border-radius: 14px !important; box-shadow: 0 4px 18px rgba(0, 0, 0, .3); }}
        [data-testid="stChatInput"]:focus-within {{ border-color: rgba(83, 230, 255, .6) !important; box-shadow: 0 0 0 3px rgba(83, 230, 255, .15), 0 4px 18px rgba(0, 0, 0, .3); }}
        [data-testid="stChatInput"] textarea {{ color: #f2f8ff !important; }}
        .credit-box {{ margin: .35rem 0 1.4rem; padding: 1rem .8rem; border: 1px solid #53e6ff; border-radius: 12px; background: rgba(5, 25, 43, .82); box-shadow: 0 0 7px #53e6ff, 0 0 18px rgba(83, 230, 255, .85), inset 0 0 12px rgba(83, 230, 255, .18); color: #edfcff; font-weight: 600; line-height: 1.55; text-align: center; text-shadow: 0 0 7px rgba(83, 230, 255, .9); }}
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: rgba(83, 230, 255, .25); border-radius: 8px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: rgba(83, 230, 255, .45); }}
    </style>
    """,
    unsafe_allow_html=True,
)

if st.session_state.user is None:
    show_auth_screen()
    st.stop()

user_id = st.session_state.user["user_id"]

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
    st.markdown(
        f'<img class="lexassist-logo-img-sidebar" src="data:image/png;base64,{LOGO_SIDEBAR_B64}" alt="LexAssist">',
        unsafe_allow_html=True,
    )
    st.caption(f"Logged in as: {st.session_state.user['name']}")
    if st.button("Log out", use_container_width=True):
        st.session_state.user = None
        st.session_state.messages = []
        st.session_state.session_id = str(uuid4())
        st.rerun()
    st.caption("Legal information, explained clearly.")
    if st.button("Start a new chat", use_container_width=True):
        clear_session_history(st.session_state.session_id)
        st.session_state.messages = []
        st.session_state.session_id = str(uuid4())
        st.rerun()
    st.divider()
    st.subheader("Previous chats")
    conversations = list_conversations(user_id)
    if not conversations:
        st.caption("Your saved chats will appear here.")
    else:
        for conversation in conversations:
            is_active = conversation["session_id"] == st.session_state.session_id
            label = f"• {conversation['title']}" if is_active else conversation["title"]
            session_id = conversation["session_id"]
            conversation_messages = get_messages(session_id)
            chat_columns = st.columns([0.84, 0.16], gap="small")
            with chat_columns[0]:
                if st.button(label, key=f"conversation-{session_id}", use_container_width=True):
                    clear_session_history(st.session_state.session_id)
                    st.session_state.session_id = session_id
                    st.session_state.messages = conversation_messages
                    st.rerun()
            with chat_columns[1]:
                with st.popover("⋮", help="Chat options", use_container_width=True):
                    st.download_button(
                        "Download chat as PDF",
                        data=create_chat_report_pdf(conversation_messages),
                        file_name="lexassist-chat-report.pdf",
                        mime="application/pdf",
                        key=f"download-chat-{session_id}",
                        use_container_width=True,
                    )
                    if st.button("Delete chat", key=f"delete-chat-{session_id}", use_container_width=True):
                        delete_conversation(session_id)
                        if is_active:
                            clear_session_history(session_id)
                            st.session_state.messages = []
                            st.session_state.session_id = str(uuid4())
                        st.rerun()
    st.divider()
    st.subheader("Before you begin")
    st.caption("LexAssist provides general information, not legal advice. Laws vary by location.")

st.markdown(
    '<div class="lexassist-brand-title main">LexAssist</div>',
    unsafe_allow_html=True,
)
st.caption("Ask about a legal topic in plain language. Include your country or state when it matters.")

for message in st.session_state.messages:
    render_message(message["role"], message["content"])
    if message["role"] == "user":
        render_user_copy_action(message)
    else:
        render_answer_actions(message)

question = st.chat_input("For example: What should I check before signing a rental agreement?")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    render_message("user", question)
    render_user_copy_action({"role": "user", "content": question})
    with st.spinner("Reviewing your question…"):
        try:
            answer = ask(question, st.session_state.session_id, owner_id=user_id)
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
