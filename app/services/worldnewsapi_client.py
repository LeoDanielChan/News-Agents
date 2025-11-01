import worldnewsapi
from worldnewsapi.rest import ApiException
from worldnewsapi.models.search_news200_response import SearchNews200Response
from pydantic import BaseModel
from google.adk.tools import FunctionTool
from typing import Dict, Any, Optional

import os
# from pprint import pprint

configuration = worldnewsapi.Configuration(
    host = "https://api.worldnewsapi.com"
)

configuration.api_key['apiKey'] = os.getenv("WORLDNEWSAPI_API_KEY")
configuration.api_key['headerApiKey'] = os.getenv("WORLDNEWSAPI_API_KEY")

# class Search_News(BaseModel):
#     text: str | None = None # str | The text to match in the news content (at least 3 characters, maximum 100 characters). By default all query terms are expected, you can use an uppercase OR to search for any terms, e.g. tesla OR ford. You can also exclude terms by putting a minus sign (-) in front of the term, e.g. tesla -ford. For exact matches just put your term in quotes, e.g. \"elon musk\". (optional)
#     text_match_indexes: str | None = None # str | If a \"text\" is given to search for, you can specify where this text is searched for. Possible values are title, content, or both separated by a comma. By default, both title and content are searched. (optional)
#     source_country: str | None = None #'mx' # str | The ISO 3166 country code from which the news should originate. (optional)
#     language: str | None = None #'es' # str | The ISO 6391 language code of the news. (optional)
#     min_sentiment: str | None = None ##-0.8 # float | The minimal sentiment of the news in range [-1,1]. (optional)
#     max_sentiment: str | None = None #0.8 # float | The maximal sentiment of the news in range [-1,1]. (optional)
#     earliest_publish_date: str | None = None #'2025-01-01 16:12:35' # str | The news must have been published after this date. (optional)
#     latest_publish_date: str | None = None #'2025-10-23 16:12:35' # str | The news must have been published before this date. (optional)
#     news_sources: str | None = None #'https://www.bbc.co.uk' # str | A comma-separated list of news sources from which the news should originate. (optional)
#     authors: str | None = None #'John Doe' # str | A comma-separated list of author names. Only news from any of the given authors will be returned. (optional)
#     categories: str | None = None #'politics,sports' # str | A comma-separated list of categories. Only news from any of the given categories will be returned. Possible categories are politics, sports, business, technology, entertainment, health, science, lifestyle, travel, culture, education, environment, other. Please note that the filter might leave out news, especially in non-English languages. If too few results are returned, use the text parameter instead. (optional)
#     entities: str | None = None #'ORG:Tesla,PER:Elon Musk' # str | Filter news by entities (see semantic types). (optional)
#     location_filter: str | None = None #'51.050407, 13.737262, 20' # str | Filter news by radius around a certain location. Format is \"latitude,longitude,radius in kilometers\". Radius must be between 1 and 100 kilometers. (optional)
#     sort: str | None = None #'publish-time' # str | The sorting criteria (publish-time). (optional)
#     sort_direction: str | None = None # str | Whether to sort ascending or descending (ASC or DESC). (optional)
#     offset: int | None = None # int | The number of news to skip in range [0,100000] (optional)
#     number: int | None = None # int | The number of news to return in range [1,100] (optional)
#     class Config:
#         arbitrary_types_allowed = True

def search_news_sources(name: str) -> Dict[str, Any]:

    """
    Searches for news sources (media outlets) that match a given name.
    Use this tool to find a source's ID before using it in another search.

    Args:
        name: The name of the news source to search for (e.g., "BBC", "CNN").

    Returns:
        A dictionary with the API response, which has two main structures:

        1. On a successful API call (even if no results are found):
           A dictionary containing an 'available' (int) key and a 'sources' (list) key.
           The LLM *must* check the 'available' key.
           - If 'available' is 0, it means no sources were found.
             (e.g., {"available": 0, "sources": []})
           - If 'available' > 0, the 'sources' list will contain the found outlets.
             (e.g., {"available": 2, "sources": [...]})

        2. On an API exception or connection error:
           A dictionary with an error status.
           (e.g., {"status": "error", "error_message": "Exception details..."})
    """

    with worldnewsapi.ApiClient(configuration) as api_client:

        api_instance = worldnewsapi.NewsApi(api_client)

        try:
            api_response = api_instance.search_news_sources(name)

            return api_response.to_dict()
        except ApiException as e:
            print(f"Exception in search_news_sources: {e}\n")
            return {"status": "error", "error_message": str(e)}

def extract_news_links(url: str) -> Dict[str, Any]:
    """
    Extracts all news article links from a single homepage or main URL.
    Use this if the user provides a general news site (e.g., "cnn.com", "bbc.com")
    and wants to see the current headlines or available article links.

    Args:
        url: The URL of the page to extract links from (e.g., "https"//www.bbc.com/news").

    Returns:
        A dictionary with the API response, which has two main structures:

        1. On a successful API call:
           A dictionary containing a 'news_links' (list) key.
           The LLM *must* check if this list is empty.
           - If 'news_links' is an empty list, it means no links were found.
             (e.g., {"news_links": []})
           - If 'news_links' is not empty, it contains the list of found URLs.
             (e.g., {"news_links": ["https://...", "https://...", ...]})

        2. On an API exception or connection error:
           A dictionary with an error status.
           (e.g., {"status": "error", "error_message": "Exception details..."})
    """
    with worldnewsapi.ApiClient(configuration) as api_client:
        api_instance = worldnewsapi.NewsApi(api_client)
        analyze = True

        try:
            api_response = api_instance.extract_news_links(url, analyze=analyze)
            
            return api_response.to_dict()
        
        except ApiException as e:
            print(f"Exception in extract_news_links: {e}\n")
            return {"status": "error", "error_message": str(e)}

def extract_news(url: str) -> Dict[str, Any]:
    """
    Extracts the full content (text, title, author) of a *single* news article
    from its specific URL. Use this when the user provides a direct link
    to an article and wants a summary, author, or the full text.

    Args:
        url: The exact URL of the article to analyze.

    Returns:
        A dictionary with the API response, which has three main structures:

        1. On a successful extraction:
           A dictionary containing the article's content, with populated 'title',
           'text', 'url', and other fields.
           (e.g., {"title": "What happens if Roe v Wade...", "text": "...", ...})

        2. On a successful API call BUT an API-level error (e.g., malformed URL):
           A dictionary where the 'title' and 'text' fields contain an error message.
           The LLM *must* check if the 'title' or 'text' contains "Error," or
           "malformed request".
           (e.g., {"title": "Error, malformed request...", "text": "...", "url": ""})

        3. On an API exception or connection error:
           A dictionary with a 'status' key indicating a system-level error.
           (e.g., {"status": "error", "error_message": "Exception details..."})
    """
    with worldnewsapi.ApiClient(configuration) as api_client:
        api_instance = worldnewsapi.NewsApi(api_client)
        analyze = True

        try:
            api_response = api_instance.extract_news(url, analyze=analyze)
            
            return api_response.to_dict()
        
        except ApiException as e:
            print(f"Exception in extract_news: {e}\n")
            return {"status": "error", "error_message": str(e)}

def search_news(
    text: Optional[str] = None,
    language: Optional[str] = None,
    news_sources: Optional[str] = None,
    earliest_publish_date: Optional[str] = None,
    latest_publish_date: Optional[str] = None,
    categories: Optional[str] = None,
    authors: Optional[str] = None,
    entities: Optional[str] = None,
    source_country: Optional[str] = None,
    min_sentiment: Optional[str] = None,
    max_sentiment: Optional[str] = None,
    location_filter: Optional[str] = None,
    sort: Optional[str] = None,
    sort_direction: Optional[str] = None,
    offset: Optional[int] = None,
    number: Optional[int] = None,
    text_match_indexes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Searches for news articles matching query text and various filters.
    This is the main tool for finding news about specific topics,
    sources, or date ranges.

    Args:
        text: The text to match (e.g., "tesla OR ford", "tesla -ford", "\"elon musk\"").
        language: The ISO 6391 language code of the news (e.g., "es", "en").
        news_sources: A comma-separated list of news source URLs (e.g., "https://www.bbc.co.uk").
        earliest_publish_date: The news must be published *after* this date
                              (format "YYYY-MM-DD HH:MM:SS").
        latest_publish_date: The news must be published *before* this date
                             (format "YYYY-MM-DD HH:MM:SS").
        categories: A comma-separated list of categories (e.g., "politics,sports").
        authors: A comma-separated list of author names (e.g., "John Doe").
        entities: Filter by semantic entities (e.g., "ORG:Tesla,PER:Elon Musk").
        source_country: The ISO 3166 country code (e.g., "mx", "us").
        min_sentiment: The minimal sentiment in range [-1,1] (e.g., "-0.8").
        max_sentiment: The maximal sentiment in range [-1,1] (e.g., "0.8").
        location_filter: Filter by radius: "latitude,longitude,radius_km"
                         (e.g., "51.05,13.73,20").
        sort: The sorting criteria (default is 'publish-time').
        sort_direction: Sort ascending or descending ("ASC" or "DESC").
        offset: The number of news to skip (e.g., 0, 10).
        number: The number of news to return, 1-100 (e.g., 10).
        text_match_indexes: Where to search for text: "title", "content", or "title,content".
                            Defaults to "title,content".

    Returns:
        A dictionary with the API response, which has three main structures:

        1. On a successful search with results:
           A dictionary where 'available' (int) > 0 and the 'news' (list)
           contains the found article objects.
           (e.g., {"available": 80, "news": [...]})

        2. On a successful search with *no* results:
           A dictionary where 'available' == 0 and the 'news' list is empty.
           (e.g., {"available": 0, "news": []})

        3. On an API exception or connection error:
           A dictionary with a 'status' key indicating a system-level error.
           (e.g., {"status": "error", "error_message": "Exception details..."})
    """
    kwargs = {
        "text": text,
        "language": language,
        "news_sources": news_sources,
        "earliest_publish_date": earliest_publish_date,
        "latest_publish_date": latest_publish_date,
        "categories": categories,
        "authors": authors,
        "entities": entities,
        "source_country": source_country,
        "min_sentiment": min_sentiment,
        "max_sentiment": max_sentiment,
        "location_filter": location_filter,
        "sort": sort,
        "sort_direction": sort_direction,
        "offset": offset,
        "number": number,
        "text_match_indexes": text_match_indexes
    }
    
    final_kwargs = {k: v for k, v in kwargs.items() if v is not None}

    with worldnewsapi.ApiClient(configuration) as api_client:
        api_instance = worldnewsapi.NewsApi(api_client)
        try:
            api_response = api_instance.search_news(**final_kwargs)
            return api_response.to_dict()
        except ApiException as e:
            print(f"Exception in search_news: {e}\n")
            return {"status": "error", "error_message": str(e)}

search_news_sources_tool = FunctionTool(func=search_news_sources)
extract_news_links_tool = FunctionTool(func=extract_news_links)
extract_news_tool = FunctionTool(func=extract_news)
search_news_tool = FunctionTool(func=search_news)