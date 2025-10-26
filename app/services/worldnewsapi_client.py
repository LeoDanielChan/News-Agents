import worldnewsapi
from worldnewsapi.rest import ApiException
from worldnewsapi.models.search_news200_response import SearchNews200Response
from pydantic import BaseModel
import os
# from pprint import pprint

configuration = worldnewsapi.Configuration(
    host = "https://api.worldnewsapi.com"
)

configuration.api_key['apiKey'] = os.getenv("WORLDNEWSAPI_API_KEY")
configuration.api_key['headerApiKey'] = os.getenv("WORLDNEWSAPI_API_KEY")

class Search_News(BaseModel):
    text: str | None = None # str | The text to match in the news content (at least 3 characters, maximum 100 characters). By default all query terms are expected, you can use an uppercase OR to search for any terms, e.g. tesla OR ford. You can also exclude terms by putting a minus sign (-) in front of the term, e.g. tesla -ford. For exact matches just put your term in quotes, e.g. \"elon musk\". (optional)
    text_match_indexes: str | None = None # str | If a \"text\" is given to search for, you can specify where this text is searched for. Possible values are title, content, or both separated by a comma. By default, both title and content are searched. (optional)
    source_country: str | None = None #'mx' # str | The ISO 3166 country code from which the news should originate. (optional)
    language: str | None = None #'es' # str | The ISO 6391 language code of the news. (optional)
    min_sentiment: str | None = None ##-0.8 # float | The minimal sentiment of the news in range [-1,1]. (optional)
    max_sentiment: str | None = None #0.8 # float | The maximal sentiment of the news in range [-1,1]. (optional)
    earliest_publish_date: str | None = None #'2025-01-01 16:12:35' # str | The news must have been published after this date. (optional)
    latest_publish_date: str | None = None #'2025-10-23 16:12:35' # str | The news must have been published before this date. (optional)
    news_sources: str | None = None #'https://www.bbc.co.uk' # str | A comma-separated list of news sources from which the news should originate. (optional)
    authors: str | None = None #'John Doe' # str | A comma-separated list of author names. Only news from any of the given authors will be returned. (optional)
    categories: str | None = None #'politics,sports' # str | A comma-separated list of categories. Only news from any of the given categories will be returned. Possible categories are politics, sports, business, technology, entertainment, health, science, lifestyle, travel, culture, education, environment, other. Please note that the filter might leave out news, especially in non-English languages. If too few results are returned, use the text parameter instead. (optional)
    entities: str | None = None #'ORG:Tesla,PER:Elon Musk' # str | Filter news by entities (see semantic types). (optional)
    location_filter: str | None = None #'51.050407, 13.737262, 20' # str | Filter news by radius around a certain location. Format is \"latitude,longitude,radius in kilometers\". Radius must be between 1 and 100 kilometers. (optional)
    sort: str | None = None #'publish-time' # str | The sorting criteria (publish-time). (optional)
    sort_direction: str | None = None # str | Whether to sort ascending or descending (ASC or DESC). (optional)
    offset: int | None = None # int | The number of news to skip in range [0,100000] (optional)
    number: int | None = None # int | The number of news to return in range [1,100] (optional)
    class Config:
        arbitrary_types_allowed = True

def search_news_sources(name: str):

    with worldnewsapi.ApiClient(configuration) as api_client:

        api_instance = worldnewsapi.NewsApi(api_client)

        try:
            api_response = api_instance.search_news_sources(name)

            return api_response
        except ApiException as e:
            print("Exception when calling NewsApi->search_news_sources: %s\n" % e)

def extract_news_links(url: str):

    with worldnewsapi.ApiClient(configuration) as api_client:

        api_instance = worldnewsapi.NewsApi(api_client)
        analyze = True

        try:
            api_response = api_instance.extract_news_links(url, analyze=analyze)

            return api_response
        except ApiException as e:
            print("Exception when calling NewsApi->extract_news_links: %s\n" % e)

def extract_news(url: str):

    with worldnewsapi.ApiClient(configuration) as api_client:

        api_instance = worldnewsapi.NewsApi(api_client)
        analyze = True
        try:
            api_response = api_instance.extract_news(url, analyze=analyze)

            return api_response
        except ApiException as e:
            print("Exception when calling NewsApi->extract_news: %s\n" % e)

def search_news(params: Search_News):

    with worldnewsapi.ApiClient(configuration) as api_client:

        api_instance = worldnewsapi.NewsApi(api_client)
        kwargs = params.model_dump(exclude_unset=True)
        try:
            # api_response = api_instance.search_news(text=dataToSearch.text, text_match_indexes=dataToSearch.text_match_indexes, source_country=dataToSearch.source_country, language=dataToSearch.language, min_sentiment=dataToSearch.min_sentiment, max_sentiment=dataToSearch.max_sentiment, earliest_publish_date=dataToSearch.earliest_publish_date, latest_publish_date=dataToSearch.latest_publish_date, news_sources=dataToSearch.news_sources, authors=dataToSearch.authors, categories=dataToSearch.categories, entities=dataToSearch.entities, location_filter=dataToSearch.location_filter, sort=dataToSearch.sort, sort_direction=dataToSearch.sort_direction, offset=dataToSearch.offset, number=dataToSearch.number)
            api_response = api_instance.search_news(**kwargs)
            return api_response.to_dict()
        except ApiException as e:
            print("Exception when calling NewsApi->Search_News: %s\n" % e)