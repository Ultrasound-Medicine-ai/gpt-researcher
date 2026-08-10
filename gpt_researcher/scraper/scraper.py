"""Web scraper module for GPT Researcher.

This module provides the Scraper class that extracts content from URLs
using various scraping backends (BeautifulSoup, PyMuPDF, Browser, etc.).
"""

import asyncio
import importlib
import logging
import subprocess
import sys

import requests
from colorama import Fore, init

from gpt_researcher.utils.workers import WorkerPool

from . import (
    ArxivScraper,
    BeautifulSoupScraper,
    BrowserScraper,
    FireCrawl,
    NoDriverScraper,
    PyMuPDFScraper,
    TavilyExtract,
    WebBaseLoaderScraper,
)


class Scraper:
    """
    Scraper class to extract the content from the links
    """

    def __init__(self, urls, user_agent, scraper, worker_pool: WorkerPool):
        """
        Initialize the Scraper class.
        Args:
            urls: List of URLs to scrape (duplicates will be removed)
        """
        # Optimization: Remove duplicate URLs to avoid redundant scraping
        unique_urls = list(dict.fromkeys(urls))  # Preserves order while removing duplicates
        duplicates_removed = len(urls) - len(unique_urls)

        self.urls = unique_urls
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.scraper = scraper
        if self.scraper == "tavily_extract":
            self._check_pkg(self.scraper)
        if self.scraper == "firecrawl":
            self._check_pkg(self.scraper)
        self.logger = logging.getLogger(__name__)
        self.worker_pool = worker_pool

        # Log deduplication results if duplicates were found
        if duplicates_removed > 0:
            self.logger.info(
                f"Removed {duplicates_removed} duplicate URL(s). "
                f"Scraping {len(unique_urls)} unique URLs instead of {len(urls)}."
            )

    async def run(self):
        """
        Extracts the content from the links
        """
        contents = await asyncio.gather(
            *(self.extract_data_from_url(url, self.session) for url in self.urls)
        )

        res = [content for content in contents if content["raw_content"] is not None]
        return res

    def _check_pkg(self, scrapper_name: str) -> None:
        """
        Checks and ensures required Python packages are available for scrapers that need
        dependencies beyond requirements.txt. When adding a new scraper to the repo, update `pkg_map`
        with its required information and call check_pkg() during initialization.
        """
        pkg_map = {
            "tavily_extract": {
                "package_installation_name": "tavily-python",
                "import_name": "tavily",
            },
            "firecrawl": {
                "package_installation_name": "firecrawl-py",
                "import_name": "firecrawl",
            },
        }
        pkg = pkg_map[scrapper_name]
        if not importlib.util.find_spec(pkg["import_name"]):
            pkg_inst_name = pkg["package_installation_name"]
            init(autoreset=True)
            print(Fore.YELLOW + f"{pkg_inst_name} not found. Attempting to install...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", pkg_inst_name]
                )
                importlib.invalidate_caches()
                print(Fore.GREEN + f"{pkg_inst_name} installed successfully.")
            except subprocess.CalledProcessError:
                raise ImportError(
                    Fore.RED
                    + f"Unable to install {pkg_inst_name}. Please install manually with "
                    f"`pip install -U {pkg_inst_name}`"
                )

    async def extract_data_from_url(self, link, session):
        """
        Extracts the data from the link with timeout/retry/max-length.

        A single URL failure never aborts the batch — returns raw_content=None
        and records degrade metadata for observability.
        """
        from gpt_researcher.utils.dep_resilience import (
            browse_chunk_max_length,
            get_circuit,
            record_degradation,
            scrape_url_retries,
            scrape_url_timeout,
        )

        scrape_cb = get_circuit("scrape")
        if not scrape_cb.allow():
            record_degradation(
                "scrape",
                "circuit_open",
                url=link,
                quality="skipped",
            )
            return {
                "url": link,
                "raw_content": None,
                "image_urls": [],
                "title": "",
                "scrape_error": "circuit_open",
                "source_quality": "skipped",
            }

        max_attempts = scrape_url_retries() + 1
        timeout = scrape_url_timeout()
        max_len = browse_chunk_max_length()
        last_err = ""

        async with self.worker_pool.throttle():
            for attempt in range(1, max_attempts + 1):
                try:
                    Scraper = self.get_scraper(link)
                    scraper = Scraper(link, session)
                    scraper_name = scraper.__class__.__name__
                    self.logger.info(f"\n=== Using {scraper_name} (attempt {attempt}) ===")

                    async def _do_scrape():
                        if hasattr(scraper, "scrape_async"):
                            return await scraper.scrape_async()
                        return await asyncio.get_running_loop().run_in_executor(
                            self.worker_pool.executor, scraper.scrape
                        )

                    content, image_urls, title = await asyncio.wait_for(
                        _do_scrape(), timeout=timeout
                    )
                    content = content or ""
                    # Traceback / error strings must not pollute context
                    if content.lstrip().startswith("Traceback") or content.startswith(
                        "Error:"
                    ):
                        raise RuntimeError("scraper returned error string")

                    if len(content) < 100:
                        scrape_cb.record_failure("too_short")
                        record_degradation(
                            "scrape",
                            "too_short",
                            url=link,
                            quality="low",
                        )
                        return {
                            "url": link,
                            "raw_content": None,
                            "image_urls": [],
                            "title": title or "",
                            "scrape_error": "too_short",
                            "source_quality": "low",
                        }

                    if max_len > 0 and len(content) > max_len:
                        content = content[:max_len]

                    scrape_cb.record_success()
                    self.logger.info(f"\nTitle: {title}")
                    self.logger.info(f"Content length: {len(content)} characters")
                    self.logger.info(f"URL: {link}")
                    self.logger.info("=" * 50)

                    return {
                        "url": link,
                        "raw_content": content,
                        "image_urls": image_urls or [],
                        "title": title or "",
                        "source_quality": "ok",
                    }

                except Exception as e:
                    last_err = str(e)
                    self.logger.error(
                        "Error processing %s (attempt %s/%s): %s",
                        link,
                        attempt,
                        max_attempts,
                        last_err,
                    )
                    if attempt < max_attempts:
                        await asyncio.sleep(min(2 ** (attempt - 1), 4))
                        continue

            scrape_cb.record_failure(last_err)
            record_degradation(
                "scrape",
                last_err[:200] or "scrape_failed",
                url=link,
                quality="failed",
            )
            return {
                "url": link,
                "raw_content": None,
                "image_urls": [],
                "title": "",
                "scrape_error": last_err[:300],
                "source_quality": "failed",
            }

    def get_scraper(self, link):
        """
        The function `get_scraper` determines the appropriate scraper class based on the provided link
        or a default scraper if none matches.

        Args:
          link: The `get_scraper` method takes a `link` parameter which is a URL link to a webpage or a
        PDF file. Based on the type of content the link points to, the method determines the appropriate
        scraper class to use for extracting data from that content.

        Returns:
          The `get_scraper` method returns the scraper class based on the provided link. The method
        checks the link to determine the appropriate scraper class to use based on predefined mappings
        in the `SCRAPER_CLASSES` dictionary. If the link ends with ".pdf", it selects the
        `PyMuPDFScraper` class. If the link contains "arxiv.org", it selects the `ArxivScraper
        """

        SCRAPER_CLASSES = {
            "pdf": PyMuPDFScraper,
            "arxiv": ArxivScraper,
            "bs": BeautifulSoupScraper,
            "web_base_loader": WebBaseLoaderScraper,
            "browser": BrowserScraper,
            "nodriver": NoDriverScraper,
            "tavily_extract": TavilyExtract,
            "firecrawl": FireCrawl,
        }

        scraper_key = None

        if link.endswith(".pdf"):
            scraper_key = "pdf"
        elif "arxiv.org" in link:
            scraper_key = "arxiv"
        else:
            scraper_key = self.scraper

        scraper_class = SCRAPER_CLASSES.get(scraper_key)
        if scraper_class is None:
            raise Exception("Scraper not found.")

        return scraper_class
