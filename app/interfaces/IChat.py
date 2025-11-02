from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class RequestChat(BaseModel):
  prompt: str
  session_id: Optional[str] = None
  
class ResponseChat(BaseModel):
  prompt: str
  response: str
  session_id: str
  
class SessionData(BaseModel):
  user_id: str
  session_id: str
  title: str
  created_at: datetime