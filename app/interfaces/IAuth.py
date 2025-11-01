from pydantic import BaseModel

class UserCredentials(BaseModel):
  """Modelo para registro e inicio de sesión."""
  email: str
  password: str