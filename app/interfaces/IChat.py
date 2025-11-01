from pydantic import BaseModel
from typing import Optional
from fastapi import Depends
from utils.getUser import get_current_user_uid

class RequestChat(BaseModel):
  prompt: str
  session_id: Optional[str] = None
  
class ResponseChat(BaseModel):
  prompt: str
  response: str
  session_id: str