import json
import re
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

# root_agent = Agent(
#   name=AGENT_NAME,
#   model=GEMINI_MODEL,
#   description='Assistant that finds news articles based on a user query.',
#   instruction="""Your sole task is to strictly use the 'search_news' tool to find a maximum of 3 articles 
#   related to the user's query. After the tool execution, 
#   you MUST return the raw JSON response (including the 'available' and 'news' keys) exactly as you received it. DO NOT summarize or comment on the results.
#   Your final output must be the pure JSON string.""",
#   tools=tools
# )

root_agent = Agent(
  name=AGENT_NAME,
  model=GEMINI_MODEL,
  description='Assistant that finds news articles based on a user query.',
  instruction="""Your sole task is to strictly use the 'search_news' tool to find a maximum of 4 articles 
  related to the user's query. 
  
  You MUST pass the user's entire query *only* to the 'text' parameter.
  You MUST NOT use any other parameters like 'earliest_publish_date', 'latest_publish_date', or 'categories', even if the user's query mentions a date or topic.
  
  After the tool execution, 
  you MUST return the raw JSON response (including the 'available' and 'news' keys) exactly as you received it. DO NOT summarize or comment on the results.
  Your final output must be the pure JSON string.""",
  tools=tools
)

# fact_checker_agent = Agent(
#   name="fact_checker_agent",
#   model=GEMINI_MODEL,
#   description='Assistant that verifies the truthfulness of a given news article text or link.',
#   instruction="""You are an expert fact-checker. Given an article URL or content, 
#   you MUST use the 'google_search' tool to find other reliable sources 
#   to confirm or deny the information. Your final output must be:
#   'VERDICT: [TRUE/FALSE/UNCERTAIN]. Evidence: [Summary of your findings with citations].'""",
#   tools=fact_check_tools
# )

# fact_checker_agent = Agent(
#   name="fact_checker_agent",
#   model=GEMINI_MODEL,
#   description='Assistant that verifies a user query using a list of related articles.',
#   instruction="""You are an expert fact-checker. Your task is to analyze a user's query and a list of related article URLs to provide a consolidated, well-reasoned verdict.

# **Chain of Thought (Internal Reasoning Steps):**
# Before generating the final output, you MUST follow this reasoning process internally:
# 1.  **Analyze the Core Query:** First, understand the central claim the user is asking about (e.g., "Is X person the president?", "Did Y event happen?").
# 2.  **Investigate & Synthesize:** For each provided URL, use the 'google_search' tool to investigate the article's content and credibility, and to find other corroborating sources.
# 3.  **Form a Verdict:** Based on all your findings, determine if the sources are consistent. 
#     * If most reliable sources agree, the verdict is TRUE or FALSE.
#     * If sources conflict, are low-quality, or there's not enough information, the verdict is AMBIGUE.
# 4.  **Draft the "Why":** Formulate a natural-language explanation (the "because...") that summarizes your synthesis. This is the most important part; it must be a clear, human-like summary of your findings.
# 5.  **Draft the "Explications":** For each article, write a brief explanation of *how* it specifically supports (or fails to support) the main verdict.

# **Final Output Format:**
# After completing your internal "Chain of Thought" reasoning, you MUST present your final answer strictly in this format. DO NOT expose your internal thought process in the output.

# The news is [TRUE/FALSE/AMBIGUE] because [Your high-level synthesis from Step 4. This must sound natural and not like a template].

# News or articles that support the veredict:

# - https://www.youtube.com/watch?v=KsZ6tROaVOQ
# - Explication: [Your brief analysis for this article from Step 5.]

# - https://www.youtube.com/watch?v=-s7TCuCpB5c
# - Explication: [Your brief analysis for this article from Step 5...]

# - https://www.netflix.com/title/80074220
# - Explication: [Your brief analysis for this article from Step 5...]
# """,
#   tools=fact_check_tools
# )

fact_checker_agent = Agent(
  name="fact_checker_agent",
  model=GEMINI_MODEL,
  description='Assistant that verifies a user query using a list of related articles.',
  instruction="""You are an expert fact-checker. Your task is to analyze a user's query and a list of related article URLs to provide a consolidated, well-reasoned verdict.

**Chain of Thought (Internal Reasoning Steps):**
1.  **Analyze the Core Query:** First, understand the central claim the user is asking about (e.g., "Is X person the president?", "Did Y event happen?").
2.  **Investigate & Synthesize:** For each provided URL, use the 'google_search' tool to investigate the article's content and credibility, and to find other corroborating sources.
3.  **Form a Verdict:** Based on all your findings, determine if the sources are consistent. 
    * If most reliable sources agree, the verdict is TRUE or FALSE.
    * If sources conflict, are low-quality, or there's not enough information, the verdict is AMBIGUE.
4.  **Draft the "Why":** Formulate a natural-language explanation (the "because...") that summarizes your synthesis from all sources.  This is the most important part; it must be a clear, human-like summary of your findings.
5.  **CURATE THE EVIDENCE (Critical):** Review all the articles you've seen. Select *ONLY* the ones that are *directly relevant* and *actively support* your final verdict. For each article, write a brief explanation of *how* it specifically supports (or fails to support) the main verdict.

**Final Output Format:**
After completing your internal "Chain of Thought", present your final answer strictly in this format.

**CRITICAL: You MUST NOT include irrelevant or "noise" articles in your final report.**

The news is [TRUE/FALSE/AMBIGUE] because [Your high-level synthesis from Step 4].

News or articles that support the veredict:

- [Relevant URL 1 (from any source)]
- Explication: [Your brief analysis for this article from Step 5.]

- [Relevant URL 2 (from any source)]
- Explication: [Your brief analysis for this article from Step 5...]
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
  article_urls = []
  
  # try:
  #   # 1. LIMPIEZA DE STRING: Quitar las vallas de código (```json y ```)
  #   cleaned_json_string = link_finder_result.strip()
    
  #   if cleaned_json_string.startswith("```json"):
  #     # Quita el encabezado de Markdown
  #     cleaned_json_string = cleaned_json_string.replace("```json", "", 1).strip()
      
  #   if cleaned_json_string.endswith("```"):
  #     # Quita el cierre de Markdown
  #     cleaned_json_string = cleaned_json_string.rstrip("`").strip()

  #   # 2. DECODIFICACIÓN JSON (raw_data ahora es un dict)
  #   raw_data = json.loads(cleaned_json_string) 
    
  #   # 3. Acceso al diccionario anidado (CORRECCIÓN FINAL)
  #   news_data = raw_data.get("search_news_response", {})
    
  #   # El resto de la lógica de depuración y extracción permanece igual
  #   # print(f"DEBUG | Datos de noticias: {news_data}")
  #   if news_data.get("available", 0) > 0 and "news" in news_data:
  #     # print(f"DEBUG | Artículos encontrados: {len(news_data['news'])}")
  #     for article in news_data["news"]:
  #       url = article.get("url")
  #       # print(f"DEBUG | url {url}")
  #       if url:
  #         # print(f"DEBUG | agrgear url: {url}")
  #         article_urls.append(url)
  #   else:
  #     return "El Agente 1 no encontró resultados de noticias para verificar."
    
  # except json.JSONDecodeError:
  #   # print(f"ERROR: El resultado del Agente 1 no es un JSON válido: {link_finder_result}")
  #   return f"Error: El Agente 1 no pudo encontrar noticias o su respuesta no fue legible: {link_finder_result[:100]}..."
  
  # except Exception as e:
  #   # print(f"ERROR FATAL al procesar la respuesta del Agente 1: {e}")
  #   return "Error inesperado al procesar la respuesta del primer agente."
  
  # if not article_urls:
  #   return "El Agente 1 encontró resultados, pero no se pudo extraer ninguna URL válida."
  
  # # print(f"URLs a verificar: {article_urls}")
  try:
    # 1. EXTRACCIÓN ROBUSTA DE JSON
    json_match = re.search(r'\{.*\}', link_finder_result, re.DOTALL)
    
    if json_match:
        cleaned_json_string = json_match.group(0)
        raw_data = json.loads(cleaned_json_string) 
        news_data = raw_data.get("search_news_response", {})
        
        # 2. EXTRACCIÓN (SI HAY RESULTADOS)
        # Extraemos los URLs si existen, pero NO detenemos el pipeline si hay 0.
        if news_data.get("available", 0) > 0 and "news" in news_data:
          for article in news_data["news"]:
            url = article.get("url")
            if url:
              article_urls.append(url)
        
        print(f"DEBUG: Agente 1 (WorldNewsAPI) encontró {len(article_urls)} artículos.")
        # HEMOS QUITADO EL 'else' QUE DEVOLVÍA EL ERROR

    else:
        # El JSON ni siquiera se encontró, pero seguimos adelante.
        print(f"WARN: Agente 1 no devolvió un JSON legible: {link_finder_result[:100]}...")

  except json.JSONDecodeError:
    # El JSON era inválido, pero seguimos adelante.
    print(f"WARN: Agente 1 devolvió un JSON inválido: {link_finder_result[:100]}...")
  
  except Exception as e:
    # Un error fatal SÍ debe detener el pipeline.
    print(f"ERROR: Error fatal procesando Agente 1: {e}")
    return f"Error inesperado al procesar la respuesta del primer agente: {type(e).__name__} - {e}"

  # Eliminamos la vieja comprobación 'if not article_urls:'

  
  # 1. Creamos el nuevo prompt consolidado para el Agente 2
  urls_to_check = article_urls[:3] # Tomamos las primeras 3
  url_list_str = "\n".join(urls_to_check)
  
  consolidated_prompt = f"""
  User's Query: "{query}"

  Related articles found:
  {url_list_str}

  Please analyze the query and the related articles, then generate the final report as per your instructions.
  """

  # 2. Llamamos al agente 'fact_checker_agent' UNA SOLA VEZ
  print(f"DEBUG | Calling fact_checker_agent with consolidated prompt for session {session_id}")
  final_response_text = await call_agent_async(
      runner_instance=runner_2, 
      session_id=session_2.id, 
      query=consolidated_prompt, 
      user_id=user_id
  )
  
  # await run_in_threadpool(save_chat_history_to_firestore, user_id, session_id, query, final_response_text)
  
  return final_response_text
