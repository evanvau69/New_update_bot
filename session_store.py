# session_store.py
user_sessions = {}

def save_session(user_id, sid, token):
    user_sessions[user_id] = {"sid": sid, "token": token}

def get_session(user_id):
    return user_sessions.get(user_id)
