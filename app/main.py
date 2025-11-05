from fastapi import FastAPI
from routes import auth_router, chat_router, worldnewsapi_router, sessions_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

@app.get("/")
def read_root():
  return {"Hello"}
  
app.include_router(worldnewsapi_router.router_worldnewsapi)
app.include_router(auth_router.auth_router)
app.include_router(chat_router.chat_router)
app.include_router(sessions_router.session_router)