from fastapi import APIRouter, Depends
from services import worldnewsapi_client

router_worldnewsapi = APIRouter()

router_worldnewsapi.prefix = '/worldnewsapi'
@router_worldnewsapi.get('/search_news_sources')
def search_news_sources(name: str):
    return worldnewsapi_client.search_news_sources(name)

@router_worldnewsapi.get('/extract_news_links')
def extract_news_links(url: str):
    return worldnewsapi_client.extract_news_links(url)

@router_worldnewsapi.get('/extract_news')
def extract_news(url: str):
    return worldnewsapi_client.extract_news(url)

@router_worldnewsapi.get('/search_news')
def search_news(params: worldnewsapi_client.Search_News = Depends()):
    return worldnewsapi_client.search_news(params)