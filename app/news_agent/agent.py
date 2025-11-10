import json
import uuid
import re
from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from news_agent.tools import tools, fact_check_tools
from starlette.concurrency import run_in_threadpool
from services.worldnewsapi_client import ( 
  extract_news
)
from utils.saveHistory import save_chat_history_to_firestore

AGENT_NAME = "news_agent"
APP_NAME = "example"
GEMINI_MODEL = "gemini-2.5-flash"

root_agent = Agent(
  name=AGENT_NAME,
  model=GEMINI_MODEL,
  description='Assistant that finds news articles based on a user query.',
  instruction="""You are a search optimization expert. Your task is to take a user's query and generate the best possible search string for the 'search_news' tool.

  1.  Analyze the user's query to identify the 3-5 most important keywords or the core topic.
  2.  If the query is a question like "Is it true that...", extract the main claim (e.g., "Earth will explode").
  3.  If the query is a news headline, extract the key entities and concepts.
  4.  You MUST call the 'search_news' tool using the refined keywords in the 'text' parameter.
  5.  You MUST set the 'number' parameter to 3.
  6.  You MUST return ONLY the raw JSON output from the tool call.
  
  Do not add any text, markdown (like ```json), or thoughts. Your output must be a valid, parseable JSON object.
  If the tool returns no results, return the empty JSON provided by the tool (e.g., {"available": 0, "news": []}).
  DO NOT say "No results found" in text.
  """,
  tools=tools
)

fact_checker_agent = Agent(
  name="fact_checker_agent",
  model=GEMINI_MODEL,
  description='Assistant that compares a list of news articles to determine overall veracity.',
  instruction="""You are an expert fact-checker and analyst. You will receive a prompt containing a list of news articles (with their original text, title, and URL) found by another agent.

Your task is to determine the overall veracity of the news event described in the articles by following these steps (Chain of Thought):

1.  **Analyze Input:** Review the list of all provided articles (up to 3).
2.  **Filter:** Identify and mentally discard any article that is clearly irrelevant, off-topic, or 'junk' (e.g., a product page, an error, or a completely different topic). These 'junk' articles MUST NOT be included in your final answer.
3.  **Compare:** Compare the content (text and titles) of the remaining, *relevant* articles. Look for consensus (Do they report the same facts?) or contradiction (Do they report opposing facts?).
4.  **Use Tools (If Needed):** You MUST use the 'google_search' tool if necessary. Use it *only* to investigate the provided, relevant URLs for more context (if their text is insufficient).
5.  **Formulate Verdict:** Based *only* on the relevant articles, decide a single, overall verdict for the user's query:
    * **TRUE:** If the relevant articles (even just one) *directly and clearly support* the claim in the user's query.
    * **FALSE:** If the relevant articles (even just one) *directly and clearly contradict* the claim in the user's query.
    * **AMBIGUE:** If the information is mixed (some articles support, some contradict), or if the relevant articles are on-topic but do not provide enough clear information to either confirm or deny the query.
6.  **Format Output:** You MUST generate your final response *only* in the following strict format. Do not add any other text before or after this structure.

The news is [VERDICT] because... [A single, concise sentence summarizing the *main finding* or *conclusion* from the articles, without mentioning "Article 1", "Article 2", etc. E.g., 'the provided articles indicate a deceleration in inflation', 'all articles confirm the same event', or 'the articles provide contradictory information'.]

The news that support this veredict are:

- [The exact URL of the first relevant article from the input]
- [Brief explanation of how this specific article supports the verdict (e.g., 'This article confirms the main fact...') or its role in your analysis.]

- [The exact URL of the second relevant article from the input]
- [Brief explanation of how this specific article supports the verdict...]

(Repeat for all *relevant* articles used. Do not include the 'junk' articles.)
""",
  tools=fact_check_tools
)

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
  
  tool_output_string = None
  final_response_text = "Error: No final text response captured." # Default
  try:
    async for event in runner_instance.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    ):
      if event.content and event.content.parts:
        for part in event.content.parts:
          if part.executable_code:
            print(f"  Debug: Agent generated code: {part.executable_code.code}")
            
          # --- CAPTURA DE SALIDA DE HERRAMIENTA (Para Agente 1) ---
          elif part.code_execution_result:
            print(f"  Debug: Code Execution Result: {part.code_execution_result.outcome}")
            if part.code_execution_result.outcome == "OK":
              tool_output_string = json.dumps(part.code_execution_result.output)
              print(f"  Debug: Captured tool output string: {tool_output_string[:200]}...")
            else:
              tool_output_string = json.dumps({"status": "error", "error_message": "Tool execution failed."})
            break
          
          elif part.text and not part.text.isspace():
            final_response_text = part.text.strip()
      
      if tool_output_string:
        print("Agent run completed (Tool output captured).")
        return tool_output_string
      
      if event.is_final_response():
        if final_response_text and not tool_output_string:
          print(f"==> Final Agent Response (Text): {final_response_text}")
          return final_response_text
        else:
          print("==> Final Agent Response: [No text, or tool output was already handled]")
          break
          
  except Exception as e:
    print(f"ERROR during agent run: {e}")
    return json.dumps({"status": "error", "error_message": f"Exception during agent run: {e}"})
  
  print("Agent run completed (Fell through loop).")
  
  if final_response_text:
    print("Returning final conversational text (fallback).")
    return final_response_text
  
  return json.dumps({"status": "error", "error_message": "Agent did not produce a tool output or a text response."})
  
  
async def run_verification_pipeline(user_id: str, query: str, session_id: str) -> str:
  
  cleaned_query = query.strip().rstrip('?').strip()
  url_match = re.search(r"https://?[\w./-?&=]+", cleaned_query)
  
  general_chat_keywords = ['hola', 'resumen', 'dame las noticias', 'qué haces', 'buenos días', 'qué puedes hacer']
  
  is_general_chat = any(keyword in cleaned_query.lower() for keyword in general_chat_keywords)
  if is_general_chat and not url_match: 
    print("DEBUG: Detectada consulta general. Respondiendo directamente.")
    response_text = "Soy un agente de verificación de noticias. Por favor envíame una pregunta específica (ej. '¿Es verdad que...') o un enlace para verificar."
    # await run_in_threadpool(save_chat_history_to_firestore, user_id, session_id, query, response_text)
    return response_text

  runner_1, session_1 = await get_runner_and_session(user_id, session_id, root_agent)
  runner_2, session_2 = await get_runner_and_session(user_id, session_id, fact_checker_agent) 
  
  search_query_for_agent1 = ""
  original_article_data = None
  article_data_list = []

  try:
    if url_match:
      url = url_match.group(0)
      print(f"DEBUG: URL detectada. Extrayendo contenido de: {url}")
      
      try:
        article = await run_in_threadpool(extract_news, url=url)
        
        if article and article.get("title") and article.get("text"):
          search_query_for_agent1 = article['title']
          original_article_data = {
            "url": article.get("url"),
            "title": article.get("title"),
            "text": article.get("text", "")[:1500]
          }
          article_data_list.append(original_article_data) 
          print(f"DEBUG: Título extraído: '{search_query_for_agent1}'. Buscando artículos similares...")
        else:
          print(f"ERROR: No se pudo extraer contenido de la URL: {url}. Respuesta API: {article}")
          return "Error: No pude extraer el contenido de la URL que proporcionaste. Puede que el enlace esté roto o no sea un artículo de noticias."
      except Exception as e:
        print(f"Error extrayendo URL individual {url}: {e}")
        return f"Error al procesar la URL: {e}"

    else:
      print("DEBUG: Query de texto detectada. Buscando artículos...")
      search_query_for_agent1 = cleaned_query

    print(f"Iniciando Agente 1 con query de búsqueda: '{search_query_for_agent1}'")
    agent_1_result = await call_agent_async(runner_1, session_1.id, search_query_for_agent1, user_id)
    print(f"DEBUG | Respuesta RAW del Agente 1: {agent_1_result[:500]}...")

    match = re.search(r'\{.*\}', agent_1_result, re.DOTALL)
    if not match:
      print(f"ERROR: No se encontró JSON en la respuesta del Agente 1. Respuesta: {agent_1_result}")
      return agent_1_result

    json_string = match.group(0)
    news_data = json.loads(json_string)

    search_response = news_data.get("search_news_response", news_data)

    if search_response.get("status") == "error":
      raise Exception(f"La API de noticias devolvió un error: {search_response.get('error_message')}")

    if "news" in search_response and search_response.get("available", 0) > 0:
      print("DEBUG: Procesando respuesta de 'search_news'")
      for article in search_response["news"]:
        if article.get("url") and (not original_article_data or article.get("url") != original_article_data["url"]):
          article_data_list.append({
            "url": article.get("url"),
            "title": article.get("title", "No Title"),
            "text": article.get("text", "")[:1500]
          })
    else:
      print("DEBUG: 'search_news' no devolvió artículos adicionales.")

  except json.JSONDecodeError as e:
    print(f"ERROR: El resultado del Agente 1 no es un JSON válido: {e}. String parseado: {json_string[:200]}...")
    return f"Error de formato (código 1.1): El agente no devolvió un formato de respuesta legible. Intenta reformular tu búsqueda."
  except Exception as e:
    print(f"ERROR FATAL en el pipeline del Agente 1: {e}")
    return f"Error inesperado al procesar la respuesta del primer agente: {e}"
  
  if not article_data_list:
    return "No se encontraron artículos de noticias relevantes para esa consulta."
  
  print(f"Total de artículos para Agente 2: {len(article_data_list)}. URLs: {[a['url'] for a in article_data_list]}")

  fact_check_prompt = f"User query: '{query}'\n\nPlease analyze the following articles and determine the veracity of the user's query:\n\n"
  for i, article in enumerate(article_data_list): # Ya está limitado (1 original + 3 búsqueda, o solo 3 de búsqueda)
    fact_check_prompt += f"--- Article {i+1} ---\n"
    fact_check_prompt += f"URL: {article['url']}\n"
    fact_check_prompt += f"Title: {article['title']}\n"
    fact_check_prompt += f"Text Snippet: {article['text']}...\n\n"

  print(f"Enviando prompt consolidado al Agente 2 (Fact-Checker)...")
  
  final_response_text = await call_agent_async(runner_2, session_2.id, fact_check_prompt, user_id)
  
  print(f"Respuesta final del Agente 2: {final_response_text}")

  # await run_in_threadpool(save_chat_history_to_firestore, user_id, session_id, query, final_response_text)
  
  return final_response_text





