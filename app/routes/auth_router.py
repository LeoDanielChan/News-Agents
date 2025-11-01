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

## Endpoint para **Iniciar Sesión** (Simulado) 🔑
@auth_router.post("/login")
async def login_user(credentials: UserCredentials):
    """
    **NOTA:** El inicio de sesión real DEBE hacerse en el cliente web/móvil,
    donde se usa el SDK de Firebase Client para obtener el ID Token.
    
    Este endpoint es un **MARCADOR DE POSICIÓN** y te indica que **DEBES** usar el token devuelto por el cliente.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="El inicio de sesión (obtener el ID Token) debe realizarse en el **cliente** (web/móvil) "
               "usando el SDK de Firebase Client. Una vez que el cliente obtiene el ID Token, "
               "debe enviarlo en el encabezado 'Authorization: Bearer <ID_TOKEN>' a las demás rutas."
    )