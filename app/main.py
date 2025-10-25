from fastapi import FastAPI
from pydantic import BaseModel
from google.adk.cli.fast_api import get_fast_api_app
from news_agent.agent import run_agent_query
import os

TOKEN = os.getenv("TOKEN")

app = FastAPI()

class RequestChat(BaseModel):
  prompt: str
  
class ResponseChat(BaseModel):
  prompt: str
  response: str

@app.get("/")
def read_root():
  return {"Hello": TOKEN}

@app.post("/start", response_model=ResponseChat)
async def start_chat(request: RequestChat):
  try:
    agent_result = await run_agent_query(request.prompt)
    return ResponseChat(
      prompt=request.prompt,
      response=agent_result,
    )
  except RuntimeError as e:
    # Handle specific error when running asyncio.run in an already running loop (like Jupyter/Colab)
    if "cannot be called from a running event loop" in str(e):
        print("\nRunning in an existing event loop (like Colab/Jupyter).")
        print("Please run `await main()` in a notebook cell instead.")

    else:
      raise e  # Re-raise other runtime errors
      
  