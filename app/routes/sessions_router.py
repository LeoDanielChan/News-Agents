from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, status
from config.db import db
from interfaces.IChat import DeleteSessionResponse, SessionData, List, SessionHistoryResponse
from starlette.concurrency import run_in_threadpool
from utils.getUser import get_current_user_uid
from google.cloud import firestore

session_router = APIRouter()

@session_router.get("/sessions", response_model=List[SessionData])
async def list_sessions(user_id: str = Depends(get_current_user_uid)):
  sessions_ref = db.collection(u'chats').document(user_id).collection(u'sessions')
  query = sessions_ref.order_by(u'created_at', direction=firestore.Query.DESCENDING).stream()
  
  sessions = []
  
  for doc in await run_in_threadpool(lambda: list(query)):
    data = doc.to_dict()
    
    created_at_dt = data.get('created_at').astimezone(timezone.utc)
    print(f"Session ID of firebase: {doc.id}", len(doc.id))
    sessions.append(SessionData(
      user_id=user_id, 
      session_id=doc.id,
      title=data.get('title', 'Conversación sin título'), 
      created_at=created_at_dt
    ))
    
  return sessions

@session_router.get("/sessions/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(session_id: str, user_id: str = Depends(get_current_user_uid)):
  messages_ref = db.collection(u'chats').document(user_id).collection(u'sessions').document(session_id).collection(u'messages').order_by(u'timestamp').stream()
  print("Fetching session history for Session ID:", session_id, len(session_id))
  history = []
  for doc in messages_ref:
    data = doc.to_dict()
    history.append({
      "author": data.get('author'),
      "text": data.get('text'),
      "timestamp": data.get('timestamp').astimezone(timezone.utc)
    })
      
  if not history:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, 
      detail="Sesión no encontrada o vacía."
    )

  return SessionHistoryResponse(session_id=session_id, messages=history)


@session_router.delete("/sessions/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(session_id: str, user_id: str = Depends(get_current_user_uid)):
  try:
    session_ref = db.collection(u'chats').document(user_id).collection(u'sessions').document(session_id)
    deleted_messages_count = await run_in_threadpool(delete_collection_and_document, session_ref)
    
    return {
      "message": f"Sesión '{session_id}' y {deleted_messages_count} mensajes eliminados correctamente."
    }
    
  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"Fallo al eliminar la sesión: {type(e).__name__}"
    )
    
def delete_collection_and_document(session_ref):
  messages_ref = session_ref.collection(u'messages').stream()
  batch = db.batch()
  deleted_count = 0
  
  for message_doc in messages_ref:
    batch.delete(message_doc.reference)
    deleted_count += 1
    
    if deleted_count % 500 == 0:
      batch.commit()
      batch = db.batch()
          
  if deleted_count > 0:
    batch.commit()
    
  session_ref.delete()
  
  return deleted_count