import firebase_admin
from firebase_admin import credentials, firestore

try:
  cred = credentials.Certificate("/app/secrets_db/news-agent.json")
  firebase_admin.initialize_app(cred)
except Exception as e:
  print(f"Error initializing Firestore: {e}")
  
db = firestore.client()