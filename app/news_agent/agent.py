from google.adk.agents.llm_agent import Agent
from google.adk.tools import google_search
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.code_executors import BuiltInCodeExecutor
from google.genai import types

AGENT_NAME = "news_agent"
APP_NAME = "example"
USER_ID = "user1234"
SESSION_ID = "session_code_exec_async"
GEMINI_MODEL = "gemini-2.5-flash"

root_agent = Agent(
  name=AGENT_NAME,
  model=GEMINI_MODEL,
  description='A helpful assistant for user questions.',
  instruction='Answer user questions to the best of your knowledge',
  tools=[google_search]
)

# Session and Runner
session_service = InMemorySessionService()

async def get_runner_and_session():
  session = await session_service.create_session(
    app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
  )
  
  runner = Runner(
    agent=root_agent, app_name=APP_NAME,
    session_service=session_service
  )
  
  return runner, session

async def call_agent_async(runner_instance, session_id, query):
  content = types.Content(role="user", parts=[types.Part(text=query)])
  
  final_response_text = "No final text response captured."
  try:
    async for event in runner_instance.run_async(
      user_id=USER_ID, session_id=session_id, new_message=content
    ):
      print(f"Event ID: {event.id}, Author: {event.author}")
      has_specific_part = False
      
      if event.content and event.content.parts:
        for part in event.content.parts:  # Iterate through all parts
          if part.executable_code:
            print(
              f"  Debug: Agent generated code:\n```python\n{part.executable_code.code}\n```"
            )
            has_specific_part = True
            
          elif part.code_execution_result:
            # Access outcome and output correctly
            print("Part:", part.code_execution_result)
            print(
              f"  Debug: Code Execution Result: {part.code_execution_result.outcome} - Output:\n{part.code_execution_result.output}"
            )
            has_specific_part = True
            
          # Also print any text parts found in any event for debugging
          elif part.text and not part.text.isspace():
            print(f"  Text: '{part.text.strip()}'")
            # Do not set has_specific_part=True here, as we want the final response logic below
            
      # --- Check for final response AFTER specific parts ---
      # Only consider it final if it doesn't have the specific code parts we just handled
      if not has_specific_part and event.is_final_response():
        print("\n--- Final Response Event Detected ---", event)
        if (
          event.content
          and event.content.parts
          and event.content.parts[0].text
        ):
          final_response_text = event.content.parts[0].text.strip()
          print(f"==> Final Agent Response: {final_response_text}")
          break
          
        else:
          print(
            "==> Final Agent Response: [No text content in final event]"
          )

  except Exception as e:
    print(f"ERROR during agent run: {e}")
    final_response_text = f"Error: {e}"
  
  return final_response_text

async def run_agent_query(query):
  global RUNNER, SESSION
  RUNNER, SESSION = await get_runner_and_session()

  return await call_agent_async(RUNNER, SESSION.id, query)



