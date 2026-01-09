"""Veo 3 API client for video generation."""

import asyncio
from pathlib import Path
from typing import Literal, Optional

import google.generativeai as genai
import structlog

from claudio.api_clients.base_client import BaseAPIClient
from claudio.config import get_config

logger = structlog.get_logger(__name__)

ResolutionType = Literal["720p", "1080p"]


class VeoClient(BaseAPIClient):
    """Client for Veo 3 video generation API via Gemini."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize the Veo client.

        Args:
            api_key: Google API key (defaults to config)
        """
        config = get_config()
        api_key = api_key or config.google_api_key

        if not api_key:
            raise ValueError("Google API key is required for Veo client")

        super().__init__(api_key=api_key)

        # Configure Gemini API
        genai.configure(api_key=api_key)

        # Use Veo 2 model (Veo 3 may not be publicly available yet)
        # Adjust model name based on actual availability
        self.model_name = "veo-002"

    async def generate_video(
        self,
        prompt: str,
        duration: float,
        end_image_path: Optional[Path] = None,
        start_image_path: Optional[Path] = None,
        resolution: ResolutionType = "1080p",
    ) -> bytes:
        """Generate a video from a text prompt with optional image constraints.

        Args:
            prompt: Text description of the video to generate
            duration: Video duration in seconds (max 8 seconds for Veo)
            end_image_path: Optional path to image for the last frame
            start_image_path: Optional path to image for the first frame
            resolution: Video resolution ("720p" or "1080p")

        Returns:
            Video data as bytes

        Raises:
            ValueError: If duration exceeds maximum (8 seconds)
            Exception: If video generation fails
        """
        config = get_config()
        max_duration = config.max_scene_duration

        if duration > max_duration:
            raise ValueError(f"Duration {duration}s exceeds maximum {max_duration}s for Veo API")

        try:
            logger.info(
                "generating_video",
                prompt_preview=prompt[:100],
                duration=duration,
                has_start_image=start_image_path is not None,
                has_end_image=end_image_path is not None,
                resolution=resolution,
            )

            # Generate video using Gemini API
            video_data = await self._retry_with_backoff(
                self._generate_video_request,
                prompt=prompt,
                duration=duration,
                start_image_path=start_image_path,
                end_image_path=end_image_path,
                resolution=resolution,
            )

            logger.info("video_generated_successfully", size_mb=len(video_data) / 1024 / 1024)
            return video_data

        except Exception as e:
            logger.error(
                "video_generation_failed",
                error=str(e),
                prompt=prompt[:100],
                duration=duration,
            )
            raise

    async def _generate_video_request(
        self,
        prompt: str,
        duration: float,
        start_image_path: Optional[Path],
        end_image_path: Optional[Path],
        resolution: ResolutionType,
    ) -> bytes:
        """Make the actual video generation request.

        Args:
            prompt: Text description of the video
            duration: Video duration in seconds
            start_image_path: Optional start frame image
            end_image_path: Optional end frame image
            resolution: Video resolution

        Returns:
            Video data as bytes
        """

        def _sync_generate() -> bytes:
            # Load images if provided
            start_image = None
            end_image = None

            if start_image_path and start_image_path.exists():
                from PIL import Image

                start_image = Image.open(start_image_path)

            if end_image_path and end_image_path.exists():
                from PIL import Image

                end_image = Image.open(end_image_path)

            # Get the model
            model = genai.GenerativeModel(self.model_name)

            # Prepare request parameters
            generation_config = {
                "duration": duration,
                "resolution": resolution,
            }

            # Build content list
            contents = [prompt]

            if start_image:
                contents.insert(0, start_image)

            if end_image:
                contents.append(end_image)

            # Generate video
            response = model.generate_content(
                contents,
                generation_config=generation_config,
            )

            # Extract video bytes from response
            # Note: The exact method may vary based on API version
            if hasattr(response, "video"):
                return response.video
            elif hasattr(response, "parts") and response.parts:
                for part in response.parts:
                    if hasattr(part, "video") or hasattr(part, "inline_data"):
                        video_data = getattr(part, "video", None) or getattr(
                            part, "inline_data", None
                        )
                        if video_data:
                            return video_data.data if hasattr(video_data, "data") else video_data

            raise ValueError("No video data in response")

        return await asyncio.to_thread(_sync_generate)

    async def generate_and_save_video(
        self,
        prompt: str,
        duration: float,
        output_path: Path,
        end_image_path: Optional[Path] = None,
        start_image_path: Optional[Path] = None,
        resolution: ResolutionType = "1080p",
    ) -> Path:
        """Generate a video and save it to disk.

        Args:
            prompt: Text description of the video to generate
            duration: Video duration in seconds
            output_path: Where to save the generated video
            end_image_path: Optional path to image for the last frame
            start_image_path: Optional path to image for the first frame
            resolution: Video resolution

        Returns:
            Path to the saved video

        Raises:
            Exception: If generation or saving fails
        """
        logger.info("generating_and_saving_video", output_path=str(output_path))

        # Generate video
        video_data = await self.generate_video(
            prompt=prompt,
            duration=duration,
            end_image_path=end_image_path,
            start_image_path=start_image_path,
            resolution=resolution,
        )

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save to disk
        import aiofiles

        async with aiofiles.open(output_path, "wb") as f:
            await f.write(video_data)

        logger.info("video_saved", path=str(output_path))
        return output_path

    def estimate_cost(self, total_duration: float) -> float:
        """Estimate the cost of generating videos.

        Args:
            total_duration: Total video duration in seconds

        Returns:
            Estimated cost in USD
        """
        config = get_config()
        return total_duration * config.veo_cost_per_second

    def calculate_scene_count(self, total_duration: float) -> int:
        """Calculate how many scenes are needed for a given duration.

        Args:
            total_duration: Total desired video duration in seconds

        Returns:
            Number of scenes needed (considering 8-second max per scene)
        """
        config = get_config()
        max_scene_duration = config.max_scene_duration
        import math

        return math.ceil(total_duration / max_scene_duration)
