from bs4 import BeautifulSoup

from gpt_researcher.retrievers.tavily.key_pool import (
    get_current_tavily_key,
    mark_tavily_key_exhausted,
    should_rotate_tavily_key,
    with_tavily_key_rotation,
)
from ..utils import get_relevant_images, extract_title


class TavilyExtract:

    def __init__(self, link, session=None):
        self.link = link
        self.session = session
        self.tavily_client = None
        self._init_client()

    def _init_client(self) -> None:
        from tavily import TavilyClient

        api_key = self.get_api_key()
        if not api_key:
            raise Exception(
                "Tavily API key not found. Set TAVILY_API_KEYS or TAVILY_API_KEY."
            )
        self.tavily_client = TavilyClient(api_key=api_key)

    def get_api_key(self) -> str:
        """
        Gets the Tavily API key
        Returns:
        Api key (str)
        """
        return get_current_tavily_key()

    def scrape(self) -> tuple:
        """
        This function extracts content from a specified link using the Tavily Python SDK, the title and
        images from the link are extracted using the functions from `gpt_researcher/scraper/utils.py`.

        Returns:
          The `scrape` method returns a tuple containing the extracted content, a list of image URLs, and
        the title of the webpage specified by the `self.link` attribute. It uses the Tavily Python SDK to
        extract and clean content from the webpage. If any exception occurs during the process, an error
        message is printed and an empty result is returned.
        """

        def _extract_with_key(api_key: str) -> tuple:
            from tavily import TavilyClient

            client = TavilyClient(api_key=api_key)
            response = client.extract(urls=self.link)
            if response["failed_results"]:
                return "", [], ""

            response_bs = self.session.get(self.link, timeout=4)
            soup = BeautifulSoup(
                response_bs.content, "lxml", from_encoding=response_bs.encoding
            )

            content = response["results"][0]["raw_content"]
            image_urls = get_relevant_images(soup, self.link)
            title = extract_title(soup)
            return content, image_urls, title

        try:
            return with_tavily_key_rotation(_extract_with_key)
        except Exception as e:
            current_key = self.get_api_key()
            if current_key and should_rotate_tavily_key(
                error_message=str(e), exception=e
            ):
                mark_tavily_key_exhausted(current_key, reason=str(e))
            print("Error! : " + str(e))
            return "", [], ""
