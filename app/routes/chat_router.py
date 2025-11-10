import uuid
from fastapi import Depends, APIRouter, HTTPException, status
from interfaces.IChat import RequestChat, ResponseChat
from news_agent.agent import run_verification_pipeline as run_agent_query
from starlette.concurrency import run_in_threadpool
from utils.getUser import get_current_user_uid
from utils.newSession import create_new_session_in_firestore

chat_router = APIRouter()

@chat_router.post("/start", response_model=ResponseChat)
async def start_chat(request: RequestChat, user_id: str = Depends(get_current_user_uid)):
  try:
    if not request.session_id:
      current_session_id = str(uuid.uuid4())
      #await run_in_threadpool(
      #  create_new_session_in_firestore,
      #  user_id,
      #  current_session_id,
      #  request.prompt
      #)
    else:
      current_session_id = request.session_id.strip()
      
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
    
  except Exception as e:
    session_info = f" (SESSION ID: {current_session_id})" if current_session_id else ""
    print(f"ERROR FATAL AL EJECUTAR AGENTE{session_info}: {type(e).__name__} - {e}")
    
    
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail="Ocurrió un error interno al procesar tu solicitud. Por favor, intenta de nuevo o inicia una nueva conversación."
    )