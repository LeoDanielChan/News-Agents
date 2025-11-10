from typing import Optional
from fastapi import HTTPException, HTTPException, Header, status
from firebase_admin import auth

def get_current_user_uid(authorization: Optional[str] = Header(None)) -> str:

  if not authorization:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Firebase ID token (Bearer) is required.",
      headers={"WWW-Authenticate": "Bearer"},
    )
  
  try:
    scheme, token = authorization.split()
    if scheme.lower() != 'bearer':
      raise ValueError("Invalid token format.")
        
    decoded_token = auth.verify_id_token(token)
    uid = decoded_token['uid']
    return uid
      
  except Exception as e:
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Token is invalid or expired: {e}",
        headers={"WWW-Authenticate": "Bearer"},
      )