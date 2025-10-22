from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel
from google.adk.cli.fast_api import get_fast_api_app
import os

TOKEN = os.getenv("TOKEN")

app: FastAPI = get_fast_api_app(
  agents_dir="./",
  web=True,
  allow_origins=["*"],
)

@app.get("/")
def read_root():
  return {"Hello": TOKEN}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
  return {"item_id": item_id, "q": q}

@app.get("/start")
async def start_chat():
  return {"status": "healthy", "adk_status": "ready"}