import json
import uuid
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
  instruction="""Your sole task is to strictly use the 'search_news' tool to find a maximum of 3 articles 
  related to the user's query. After the tool execution, 
  you MUST return the raw JSON response (including the 'available' and 'news' keys) exactly as you received it. DO NOT summarize or comment on the results.
  Your final output must be the pure JSON string.""",
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
  # print(f"DEBUG | Respuesta RAW del Agente 1 (JSON): {link_finder_result}")
  
  articles_to_verify = []
  
  try:
    # 1. EXTRACCIÓN ROBUSTA DE JSON (MÉTODO 3: HÍBRIDO)
    
    # Buscar el inicio del bloque de código JSON
    start_marker = "```json"
    start_index = link_finder_result.find(start_marker)
    
    if start_index != -1:
      # Si se encontró "```json", buscar el primer '{' DESPUÉS de ese marcador
      start_index = link_finder_result.find('{', start_index + len(start_marker))
    else:
      # Si no se encontró "```json", buscar el primer '{' en todo el string
      start_index = link_finder_result.find('{')

    # Buscar el último '}'
    end_index = link_finder_result.rfind('}')

    # Validar que encontramos ambos marcadores en el orden correcto
    if start_index == -1 or end_index == -1 or end_index < start_index:
      # Si no se encuentran marcadores de objeto JSON válidos, lanzamos el error
      raise json.JSONDecodeError("No se encontró un objeto JSON en la respuesta del agente", link_finder_result, 0)
        
    # Extraemos la porción del string que es (con suerte) JSON
    cleaned_json_string = link_finder_result[start_index : end_index + 1]

    # 2. DECODIFICACIÓN JSON
    raw_data = json.loads(cleaned_json_string)

    # 3. ACCESO ROBUSTO A LOS DATOS (Esto ya lo tenías y es correcto)
    news_data = {}
    
    # Opción 1: El JSON está anidado (como antes)
    # {"search_news_response": {"available": 480, "news": [...]}}
    if "search_news_response" in raw_data and raw_data.get("search_news_response"):
        news_data = raw_data.get("search_news_response")
    
    # Opción 2: El JSON es crudo (como en el error)
    # {"available": 480, "news": [...]}
    elif "available" in raw_data and "news" in raw_data:
        news_data = raw_data
    
    # Si news_data sigue vacío, el JSON no tenía ningún formato esperado.

    # 4. Lógica de extracción (ahora usa el news_data corregido)
    # print(f"DEBUG | Datos de noticias: {news_data}")
    if news_data.get("available", 0) > 0 and "news" in news_data:
      # MODIFICACIÓN: Extraer Título, URL y Texto (limitado a 3 artículos)
      for article in news_data["news"][:3]: 
        url = article.get("url")
        text = article.get("text", "")
        title = article.get("title", "")
        
        if url:
          articles_to_verify.append({"url": url, "title": title, "text": text})
    else:
      return "El Agente 1 no encontró resultados de noticias para verificar."
    
  except json.JSONDecodeError:
    # print(f"ERROR: El resultado del Agente 1 no es un JSON válido: {link_finder_result}")
    return f"Error: El Agente 1 no pudo encontrar noticias o su respuesta no fue legible: {link_finder_result[:100]}..."
  
  except Exception as e:
    # print(f"ERROR FATAL al procesar la respuesta del Agente 1: {e}")
    return "Error inesperado al procesar la respuesta del primer agente."
  
  if not articles_to_verify:
    return "El Agente 1 encontró resultados, pero no se pudo extraer ninguna URL válida."
  
  # --- INICIO DE CAMBIOS EN LA LÓGICA DEL PIPELINE ---

  # 1. Formatear un ÚNICO prompt para el Agente 2
  # INCLUIMOS LA CONSULTA ORIGINAL DEL USUARIO (query)
  fact_check_prompt = f"La consulta original del usuario es: \"{query}\"\n\n"
  fact_check_prompt += "Por favor, analiza los siguientes artículos para determinar si la consulta del usuario es VERDADERA, FALSA o AMBIGUA basándote *estrictamente* en esta evidencia:\n\n"
  
  for i, article in enumerate(articles_to_verify):
    fact_check_prompt += f"Artículo {i+1}:\n"
    fact_check_prompt += f"URL: {article['url']}\n"
    fact_check_prompt += f"Title: {article['title']}\n"
    # Truncamos el texto para evitar prompts demasiado largos
    fact_check_prompt += f"Text: {article['text'][:500]}...\n\n"

  # 2. Llamar al Agente 2 UNA SOLA VEZ (se elimina el bucle 'for')
  final_response_text = await call_agent_async(runner_2, session_2.id, fact_check_prompt, user_id)
  
  # --- FIN DE CAMBIOS EN LA LÓGICA DEL PIPELINE ---
  
  # await run_in_threadpool(save_chat_history_to_firestore, user_id, session_id, query, final_response_text)
  
  return final_response_text

