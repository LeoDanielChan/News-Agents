from google.adk.tools import google_search
from services.worldnewsapi_client import search_news_sources_tool, extract_news_links_tool, extract_news_tool, search_news_tool

tools = [
    google_search, search_news_sources_tool, extract_news_links_tool, extract_news_tool, search_news_tool
]
