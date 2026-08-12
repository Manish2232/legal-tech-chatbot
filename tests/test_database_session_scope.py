import database


def test_list_conversations_is_scoped_to_a_session(monkeypatch, tmp_path):
    db_path = tmp_path / "lexassist.db"
    monkeypatch.setattr(database, "DATABASE_PATH", db_path)

    database.initialize_database()
    database.save_message("session-a", "user", "What is tenant screening?")
    database.save_message("session-a", "assistant", "Tenant screening is a process.")
    database.save_message("session-b", "user", "What is a power of attorney?")
    database.save_message("session-b", "assistant", "A power of attorney lets someone act for you.")

    session_a_chats = database.list_conversations("session-a")
    session_b_chats = database.list_conversations("session-b")

    assert [chat["session_id"] for chat in session_a_chats] == ["session-a"]
    assert [chat["session_id"] for chat in session_b_chats] == ["session-b"]
