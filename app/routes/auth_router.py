from fastapi import APIRouter, HTTPException, status
from firebase_admin import auth
from interfaces.IAuth import UserCredentials

auth_router = APIRouter()
auth_router.prefix = '/auth'

@auth_router.post("/register")
async def register_user(credentials: UserCredentials):
    try:
        user = auth.create_user(
            email=credentials.email,
            password=credentials.password
        )
        return {"message": "Usuario registrado exitosamente.", "uid": user.uid}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Fallo en el registro: {e}"
        )