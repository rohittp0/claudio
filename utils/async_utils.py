"""Async utility functions for parallel processing."""

import asyncio
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")


async def gather_with_concurrency(
    n: int, *tasks: Awaitable[T], return_exceptions: bool = False
) -> list[T | BaseException]:
    """Execute async tasks with limited concurrency.

    Args:
        n: Maximum number of concurrent tasks
        *tasks: Async tasks to execute
        return_exceptions: If True, exceptions are returned instead of raised

    Returns:
        List of results from all tasks
    """
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task: Awaitable[T]) -> T:
        async with semaphore:
            return await task

    return await asyncio.gather(
        *[sem_task(task) for task in tasks], return_exceptions=return_exceptions
    )


async def retry_async(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    **kwargs: Any,
) -> T:
    """Retry an async function with exponential backoff.

    Args:
        func: The async function to retry
        *args: Positional arguments for func
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for each retry
        **kwargs: Keyword arguments for func

    Returns:
        Result from successful function call

    Raises:
        The last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = delay * (backoff**attempt)
                await asyncio.sleep(wait_time)
            else:
                raise

    if last_exception:
        raise last_exception
    raise RuntimeError("Retry failed unexpectedly")


async def run_with_timeout(coro: Awaitable[T], timeout: float) -> T:
    """Run a coroutine with a timeout.

    Args:
        coro: The coroutine to run
        timeout: Timeout in seconds

    Returns:
        Result from the coroutine

    Raises:
        asyncio.TimeoutError: If timeout is exceeded
    """
    return await asyncio.wait_for(coro, timeout=timeout)


class ProgressTracker:
    """Track progress of parallel operations."""

    def __init__(self, total: int) -> None:
        """Initialize progress tracker.

        Args:
            total: Total number of tasks
        """
        self.total = total
        self.completed = 0
        self.failed = 0
        self._lock = asyncio.Lock()

    async def mark_completed(self) -> None:
        """Mark a task as completed."""
        async with self._lock:
            self.completed += 1

    async def mark_failed(self) -> None:
        """Mark a task as failed."""
        async with self._lock:
            self.failed += 1

    def get_progress(self) -> tuple[int, int, int]:
        """Get current progress.

        Returns:
            Tuple of (completed, failed, remaining)
        """
        remaining = self.total - self.completed - self.failed
        return (self.completed, self.failed, remaining)

    def get_progress_string(self) -> str:
        """Get progress as a formatted string.

        Returns:
            Progress string (e.g., "Completed: 3/5, Failed: 0, Remaining: 2")
        """
        completed, failed, remaining = self.get_progress()
        return f"Completed: {completed}/{self.total}, Failed: {failed}, Remaining: {remaining}"

    def is_complete(self) -> bool:
        """Check if all tasks are complete."""
        return (self.completed + self.failed) == self.total

    def has_failures(self) -> bool:
        """Check if any tasks failed."""
        return self.failed > 0


async def batch_process(
    items: list[T],
    processor: Callable[[T], Awaitable[Any]],
    batch_size: int = 5,
    progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
) -> list[Any]:
    """Process items in batches with progress tracking.

    Args:
        items: List of items to process
        processor: Async function to process each item
        batch_size: Number of items to process concurrently
        progress_callback: Optional callback for progress updates (completed, total)

    Returns:
        List of results from processing all items
    """
    results = []
    total = len(items)

    for i in range(0, total, batch_size):
        batch = items[i : i + batch_size]
        batch_results = await asyncio.gather(*[processor(item) for item in batch])
        results.extend(batch_results)

        if progress_callback:
            await progress_callback(min(i + batch_size, total), total)

    return results
