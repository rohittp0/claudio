"""Base client with common API functionality."""

import asyncio
from typing import Any, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)


class BaseAPIClient:
    """Base class for API clients with retry logic and error handling."""

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: float = 300.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize the base API client.

        Args:
            api_key: API key for authentication
            base_url: Optional base URL for the API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "BaseAPIClient":
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()

    async def _retry_with_backoff(
        self, func: Any, *args: Any, **kwargs: Any
    ) -> Any:
        """Retry a function with exponential backoff.

        Args:
            func: The async function to retry
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function call

        Raises:
            The last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except httpx.HTTPStatusError as e:
                last_exception = e

                # Don't retry client errors (4xx) except rate limits
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    logger.error(
                        "client_error",
                        status_code=e.response.status_code,
                        response=e.response.text,
                    )
                    raise

                # Retry server errors (5xx) and rate limits (429)
                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        "retrying_request",
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        wait_time=wait_time,
                        error=str(e),
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("max_retries_exceeded", error=str(e))
                    raise

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e

                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        "retrying_request",
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        wait_time=wait_time,
                        error=str(e),
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("max_retries_exceeded", error=str(e))
                    raise

        if last_exception:
            raise last_exception

        raise RuntimeError("Retry failed unexpectedly")
