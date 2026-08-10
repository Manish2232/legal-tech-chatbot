from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

load_dotenv()

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

while True:
    question = input("\nYou: ")

    if question.lower() in ["exit", "quit"]:
        print("Chat ended.")
        break

    response = chatbot.invoke(
        {"question": question},
        config={"configurable": {"session_id": session_id}}
    )

    print("\nLegal Assistant:", response.content)