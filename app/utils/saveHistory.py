from config.db import db
from google.cloud import firestore

def save_chat_history_to_firestore(user_id, session_id, user_message, agent_response):
  doc_ref = db.collection(u'chats').document(user_id).collection(u'sessions').document(session_id)
  
  doc_ref.collection(u'messages').add({
    u'author': u'user',
    u'text': user_message,
    u'timestamp': firestore.SERVER_TIMESTAMP,
  })
  
  doc_ref.collection(u'messages').add({
    u'author': u'agent',
    u'text': agent_response,
    u'timestamp': firestore.SERVER_TIMESTAMP,
  })
  
  print(len(session_id), "Saving chat history to Firestore...")
  
  print(f"History saved: {user_id}, Session: {session_id}")
