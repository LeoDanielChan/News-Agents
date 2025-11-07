import json
from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from news_agent.tools import tools, fact_check_tools
from starlette.concurrency import run_in_threadpool
from utils.saveHistory import save_chat_history_to_firestore

AGENT_NAME = "news_agent"
APP_NAME = "example"
GEMINI_MODEL = "gemini-2.5-flash"

root_agent = Agent(
  name=AGENT_NAME,
  model=GEMINI_MODEL,
  description='Assistant that finds news articles based on a user query.',
  instruction="""Your only task is to use the 'search_news' tool to find a maximum of 3 articles 
  related to the user's query and return the raw JSON result. Do not summarize or comment on the results.""",
  tools=tools
)

fact_checker_agent = Agent(
  name="fact_checker_agent",
  model=GEMINI_MODEL,
  description='Assistant that verifies the truthfulness of a given news article text or link.',
  instruction="""You are an expert fact-checker. Given an article URL or content, 
  you MUST use the 'google_search' tool to find other reliable sources 
  to confirm or deny the information. Your final output must be:
  'VERDICT: [TRUE/FALSE/UNCERTAIN]. Evidence: [Summary of your findings with citations].'""",
  tools=fact_check_tools
)

# Session and Runner
session_service = InMemorySessionService()

async def get_runner_and_session(user_id: str, session_id: str, agent: Agent):
  session = None
  try:
    session = await session_service.create_session(
      app_name=APP_NAME,
      user_id=user_id,
      session_id=session_id
    )
    
  except Exception as e:
    msg = str(e)
    
    if "AlreadyExists" in msg or "already exists" in msg:
      
      try:
        session = await session_service.get_session(
          app_name=APP_NAME, 
          user_id=user_id, 
          session_id=session_id
        )

      except Exception as retrieve_error:
        print(f"ERROR: Fallo al recuperar la sesión existente: {retrieve_error}")
        raise retrieve_error

    else:
      raise
    
  if session is None:
    raise RuntimeError("Failed to obtain a session object. Check the inner exception details.")
  
  runner = Runner(
      agent=agent,
      app_name=APP_NAME,
      session_service=session_service
    )
  
    
  return runner, session

async def call_agent_async(runner_instance: Runner, session_id: str, query: str, user_id: str) -> str:
  content = types.Content(role="user", parts=[types.Part(text=query)])
  
  final_response_text = "No final text response captured."
  try:
    async for event in runner_instance.run_async(
      user_id=user_id, session_id=session_id, new_message=content
    ):
      has_specific_part = False
      
      if event.content and event.content.parts:
        for part in event.content.parts:
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
            pass
            #print(f"  Text: '{part.text.strip()}'")
            # Do not set has_specific_part=True here, as we want the final response logic below
            
      # --- Check for final response AFTER specific parts ---
      # Only consider it final if it doesn't have the specific code parts we just handled
      if not has_specific_part and event.is_final_response():
        if (
          event.content
          and event.content.parts
          and event.content.parts[0].text
        ):
          final_response_text = event.content.parts[0].text.strip()
          #print(f"==> Final Agent Response: {final_response_text}")
          break
          
        else:
          pass
          #print(
          #  "==> Final Agent Response: [No text content in final event]"
          #)

  except Exception as e:
    print(f"ERROR during agent run: {e}")
    final_response_text = f"Error: {e}"
    
  
  print("Agent run completed.")
  
  return final_response_text

async def run_verification_pipeline(user_id: str, query: str, session_id: str) -> str:
  runner_1, session_1 = await get_runner_and_session(user_id, session_id, root_agent)
  runner_2, session_2 = await get_runner_and_session(user_id, session_id, fact_checker_agent)  

  link_finder_result = await call_agent_async(runner_1, session_1.id, query, user_id)
  
  article_urls = []
  
  try:
    news_data = json.loads(link_finder_result)

    if news_data.get("available", 0) > 0 and "news" in news_data:
      for article in news_data["news"]:
        url = article.get("url")
        if url:
          article_urls.append(url)
    else:
      return "El Agente 1 no encontró resultados de noticias para verificar."
    
  except json.JSONDecodeError:
    print(f"ERROR: El resultado del Agente 1 no es un JSON válido: {link_finder_result}")
    return f"Error: El Agente 1 no pudo encontrar noticias o su respuesta no fue legible: {link_finder_result[:100]}..."
  
  except Exception as e:
    print(f"ERROR FATAL al procesar la respuesta del Agente 1: {e}")
    return "Error inesperado al procesar la respuesta del primer agente."
  
  if not article_urls:
    return "El Agente 1 encontró resultados, pero no se pudo extraer ninguna URL válida."
  
  print(f"URLs a verificar: {article_urls}")

  final_verdicts = []
  
  for url in article_urls[:3]:
    fact_check_prompt = f"Verifica la veracidad de la noticia en este enlace: {url}"

    verdict = await call_agent_async(runner_2, session_2.id, fact_check_prompt, user_id)
    final_verdicts.append(f"Resultado para {url}:\n{verdict}")
    
  final_response_text = "\n\n".join(final_verdicts)
  
  await run_in_threadpool(save_chat_history_to_firestore, user_id, session_id, query, final_response_text)
  
  return final_response_text