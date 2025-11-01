from datetime import timezone
import uuid
from fastapi import Depends, FastAPI, HTTPException, status
from config.db import db
from interfaces.IChat import RequestChat, ResponseChat
from news_agent.agent import run_agent_query
from routes import auth_router, worldnewsapi_router
import os

from utils.getUser import get_current_user_uid
from utils.newSession import create_new_session_in_firestore

TOKEN = os.getenv("TOKEN")

app = FastAPI()

@app.get("/")
def read_root():
  return {"Hello": TOKEN}

@app.post("/start", response_model=ResponseChat)
async def start_chat(request: RequestChat, user_id: str = Depends(get_current_user_uid)):
  try:
    if not request.session_id:
      current_session_id = str(uuid.uuid4())
      await create_new_session_in_firestore(user_id, current_session_id, request.prompt)
    else:
      current_session_id = request.session_id
        
    agent_result = await run_agent_query(
      user_id=user_id, 
      query=request.prompt, 
      session_id=current_session_id
    )

    return ResponseChat(
      prompt=request.prompt,
      response=agent_result,
      session_id=current_session_id
    )
    
  except RuntimeError as e:
    if "cannot be called from a running event loop" in str(e):
      print("\nRunning in an existing event loop (like Colab/Jupyter).")
      print("Please run `await main()` in a notebook cell instead.")

    else:
      raise e
    
@app.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str, user_id: str = Depends(get_current_user_uid)):
    """
    Devuelve todos los mensajes de una conversación específica.
    """
    messages_ref = db.collection(u'chats').document(user_id).collection(u'sessions').document(session_id).collection(u'messages').order_by(u'timestamp').stream()
    
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
        
    return {"session_id": session_id, "messages": history}


## Endpoint para **Eliminar una Sesión** 🗑️
@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user_id: str = Depends(get_current_user_uid)):
    """
    Elimina permanentemente una conversación y su historial asociado.
    """
    try:
        session_ref = db.collection(u'chats').document(user_id).collection(u'sessions').document(session_id)
        
        # Opcional: Eliminar todos los mensajes dentro de la subcolección (requiere iteración)
        # Una alternativa más simple y escalable es depender de las Cloud Functions para esto
        
        session_ref.delete()
        
        return {"message": f"Sesión '{session_id}' eliminada correctamente."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fallo al eliminar la sesión: {e}"
        )
      
app.include_router(worldnewsapi_router.router_worldnewsapi)
app.include_router(auth_router.auth_router)