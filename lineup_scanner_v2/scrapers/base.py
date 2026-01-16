"""
Base scraper with retry logic and logging
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import config

logger = logging.getLogger("nba_scanner.scrapers")


class BaseScraper(ABC):
    """Abstract base class for all scrapers"""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }
    
    @retry(
        stop=stop_after_attempt(config.max_retries),
        wait=wait_exponential(multiplier=config.retry_delay, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Retry {retry_state.attempt_number}/{config.max_retries} after error"
        )
    )
    async def fetch(self, client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
        """Fetch URL with retry logic"""
        logger.debug(f"Fetching: {url}")
        response = await client.get(url, headers=self.headers, timeout=15.0, **kwargs)
        response.raise_for_status()
        return response
    
    @abstractmethod
    async def scrape(self, client: httpx.AsyncClient) -> Any:
        """Main scrape method - implement in subclass"""
        pass
