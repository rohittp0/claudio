"""Base client with common API functionality."""

import asyncio
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class BaseAPIClient:
    """Base class for API clients with retry logic and error handling."""

    def __init__(
        self,
        api_key: str,
        max_retries: int = 3,
    ) -> None:
        """Initialize the base API client.

        Args:
            api_key: API key for authentication
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key
        self.max_retries = max_retries

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
            except Exception as e:
                last_exception = e
                error_str = str(e)

                # Check if this is a rate limit error (429) or server error (5xx)
                # that should be retried
                should_retry = (
                    "429" in error_str
                    or "rate limit" in error_str.lower()
                    or "500" in error_str
                    or "503" in error_str
                    or "timeout" in error_str.lower()
                    or "network" in error_str.lower()
                )

                # Don't retry client errors (4xx) except rate limits
                if not should_retry and any(
                    code in error_str for code in ["400", "401", "403", "404"]
                ):
                    logger.error("client_error", error=error_str)
                    raise

                # Retry on transient errors
                if attempt < self.max_retries - 1 and should_retry:
                    wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        "retrying_request",
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        wait_time=wait_time,
                        error=error_str,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("max_retries_exceeded", error=error_str)
                    raise

        if last_exception:
            raise last_exception

        raise RuntimeError("Retry failed unexpectedly")
