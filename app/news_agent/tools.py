from google.adk.tools import google_search
from services.worldnewsapi_client import search_news_sources_tool, extract_news_links_tool, extract_news_tool, search_news_tool

tools = [
    # search_news_sources_tool, # buscar fuentes de noticias
    # extract_news_links_tool, # extraer enlaces de noticias de una fuente
    # extract_news_tool, # extraer contenido de una noticia
    search_news_tool # buscar noticias por titulo de noticia o palabra clave
]

fact_check_tools = [
    google_search
]