from typing import Optional
from fastapi import HTTPException, HTTPException, Header, status
from firebase_admin import auth

def get_current_user_uid(authorization: Optional[str] = Header(None)) -> str:
  """
  Verifica el token JWT de Firebase y devuelve el UID del usuario.
  Se usa como una dependencia de FastAPI para proteger rutas.
  """
  if not authorization:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Se requiere un token de Firebase ID (Bearer).",
      headers={"WWW-Authenticate": "Bearer"},
    )
  
  try:
    scheme, token = authorization.split()
    if scheme.lower() != 'bearer':
      raise ValueError("Formato de token no válido.")
        
    decoded_token = auth.verify_id_token(token)
    uid = decoded_token['uid']
    return uid
      
  except Exception as e:
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Token inválido o expirado: {e}",
        headers={"WWW-Authenticate": "Bearer"},
      )