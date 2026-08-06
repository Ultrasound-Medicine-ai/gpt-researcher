"""Tavily API search retriever for GPT Researcher.

This module provides the TavilySearch class for performing web searches
using the Tavily API.
"""

import json
import logging
from typing import Literal, Sequence

import requests

from .key_pool import (
    get_current_tavily_key,
    mark_tavily_key_exhausted,
    parse_http_error_response,
    should_rotate_tavily_key,
)

logger = logging.getLogger(__name__)


class TavilySearch:
    """
    Tavily API Retriever
    """

    def __init__(self, query, headers=None, topic="general", query_domains=None):
        """
        Initializes the TavilySearch object.

        Args:
            query (str): The search query string.
            headers (dict, optional): Additional headers to include in the request. Defaults to None.
            topic (str, optional): The topic for the search. Defaults to "general".
            query_domains (list, optional): List of domains to include in the search. Defaults to None.
        """
        self.query = query
        self.request_headers = headers or {}
        self.topic = topic
        self.base_url = "https://api.tavily.com/search"
        self.api_key = self.get_api_key()
        self.http_headers = {
            "Content-Type": "application/json",
        }
        self.query_domains = query_domains or None

    def get_api_key(self):
        """
        Gets the Tavily API key
        Returns:

        """
        return get_current_tavily_key(self.request_headers)

    def _search(
        self,
        query: str,
        search_depth: Literal["basic", "advanced"] = "basic",
        topic: str = "general",
        days: int = 2,
        max_results: int = 10,
        include_domains: Sequence[str] = None,
        exclude_domains: Sequence[str] = None,
        include_answer: bool = False,
        include_raw_content: bool = False,
        include_images: bool = False,
        use_cache: bool = True,
        api_key: str | None = None,
    ) -> dict:
        """
        Internal search method to send the request to the API.
        """

        data = {
            "query": query,
            "search_depth": search_depth,
            "topic": topic,
            "days": days,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "max_results": max_results,
            "include_domains": include_domains,
            "exclude_domains": exclude_domains,
            "include_images": include_images,
            "api_key": api_key or self.api_key,
            "use_cache": use_cache,
        }

        response = requests.post(
            self.base_url, data=json.dumps(data), headers=self.http_headers, timeout=100
        )

        if response.status_code == 200:
            return response.json()

        status_code, body = parse_http_error_response(response)
        if should_rotate_tavily_key(status_code=status_code, error_message=body):
            mark_tavily_key_exhausted(data["api_key"], reason=body or str(status_code))
            raise RuntimeError(body or f"Tavily request failed with status {status_code}")

        response.raise_for_status()
        return {}

    def search(self, max_results=10):
        """
        Searches the query
        Returns:

        """
        search_response = []
        tried_keys: set[str] = set()

        while True:
            api_key = self.get_api_key()
            if not api_key or api_key in tried_keys:
                break
            tried_keys.add(api_key)

            try:
                results = self._search(
                    self.query,
                    search_depth="basic",
                    max_results=max_results,
                    topic=self.topic,
                    include_domains=self.query_domains,
                    api_key=api_key,
                )
                sources = results.get("results", [])
                if not sources:
                    raise Exception("No results found with Tavily API search.")
                search_response = [
                    {"href": obj["url"], "body": obj["content"]} for obj in sources
                ]
                self.api_key = api_key
                break
            except Exception as e:
                if api_key and should_rotate_tavily_key(error_message=str(e), exception=e):
                    mark_tavily_key_exhausted(api_key, reason=str(e))
                    continue

                logger.error(
                    "Tavily search failed: %s. Failed fetching sources.", e
                )
                break

        if not search_response and tried_keys:
            logger.error(
                "All attempted Tavily API keys failed for query: %s", self.query
            )

        return search_response
