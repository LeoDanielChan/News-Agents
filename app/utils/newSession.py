from config.db import db
from google.cloud import firestore

def create_new_session_in_firestore(user_id: str, session_id: str, initial_prompt: str):
  
  title = initial_prompt[:50] + ("..." if len(initial_prompt) > 50 else "")
  db.collection(u'chats').document(user_id).collection(u'sessions').document(session_id).set({
    u'title': title,
    u'created_at': firestore.SERVER_TIMESTAMP,
    u'user_id': user_id
  })