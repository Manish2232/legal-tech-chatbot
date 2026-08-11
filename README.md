# LexAssist

LexAssist is a legal-information chatbot that translates common legal topics into clear, practical language. It is designed as an educational tool—not a substitute for a qualified lawyer.

## Why this project stands out

- **Responsible AI behaviour:** clear legal-information boundaries, jurisdiction-aware responses, uncertainty handling, and urgent-situation guidance.
- **Persistent conversation history:** a local SQLite database stores every completed chat. Users can reopen earlier conversations from the sidebar, even after restarting the app.
- **Conversation memory:** each active chat retains a bounded context for relevant follow-up questions while preventing unlimited AI context growth.
- **Reliable user experience:** configuration checks, question validation, API retry settings, friendly error messages, and a one-click new-chat control.
- **Clean architecture:** the reusable AI core in `model.py` is independent from the Streamlit interface in `app.py`, making the code easier to test and extend.

## Tech stack

Python, Streamlit, LangChain Core, Mistral AI, and python-dotenv.

The application creates `lexassist.db` automatically in the project folder on first run. This is a local SQLite file that holds saved chats; do not commit it if it contains real user conversations.

To create the database before starting the application, run:

```bash
python database.py
```

## Run locally

1. Create and activate a virtual environment.
2. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Add a `.env` file in the project folder:

   ```env
   MISTRAL_API_KEY=your_mistral_api_key
   # Optional: LEXASSIST_MODEL=mistral-small-2506
   ```

4. Start the web app:

   ```bash
   streamlit run app.py
   ```

   Or test the assistant in the terminal:

   ```bash
   python model.py
   ```

## Resume description

Built **LexAssist**, a responsible legal-information chatbot using Python, Streamlit, LangChain, Mistral AI, and SQLite. Implemented persistent chat history with conversation recovery, session-based conversational memory, input validation, configurable model settings, resilient error handling, and legal-safety guardrails for clear jurisdiction-aware responses.

## Important note

LexAssist provides general legal information only. It does not provide legal advice or form an attorney-client relationship.
