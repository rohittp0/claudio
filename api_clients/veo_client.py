"""Veo 3 API client for video generation."""

import asyncio
from pathlib import Path
from typing import Literal, Optional

import structlog
from google import genai

from api_clients.base_client import BaseAPIClient
from config import get_config

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

        # Create Gemini client
        self.client = genai.Client(api_key=api_key)

        # Use Veo 3.1 model
        self.model_name = "veo-3.1-generate-preview"

    async def generate_and_save_video(
        self,
        prompt: str,
        output_path: Path,
        end_image_path: Path,
        start_image_path: Path,
    ):
        """Generate a video from a text prompt with start and end frame images.

        Both start and end images are required for Veo 3.1's interpolation mode.

        Args:
            prompt: Text description of the video
            output_path: Path to save the generated video
            end_image_path: Path to the end-frame image (required)
            start_image_path: Path to the start-frame image (required)
        """
        try:
            logger.info(
                "generating_video",
                prompt_preview=prompt[:100],
                has_start_image=start_image_path is not None,
                has_end_image=end_image_path is not None,
            )

            # Validate both images exist
            if not start_image_path or not start_image_path.exists():
                raise ValueError(f"Start image is required but not found: {start_image_path}")
            if not end_image_path or not end_image_path.exists():
                raise ValueError(f"End image is required but not found: {end_image_path}")

            # Generate video using Gemini API
            await self._retry_with_backoff(
                self._generate_video_request,
                prompt=prompt,
                start_image_path=start_image_path,
                end_image_path=end_image_path,
                output_path=output_path,
            )

            logger.info("video_generated_successfully")
            return output_path

        except Exception as e:
            logger.error(
                "video_generation_failed",
                error=str(e),
                prompt=prompt[:100],
            )
            raise

    async def _generate_video_request(
        self,
        prompt: str,
        start_image_path: Path,
        end_image_path: Path,
        output_path: Path
    ):
        """Make the actual video generation request.

        Both start and end images are required for Veo 3.1's interpolation mode.

        Args:
            prompt: Text description of the video
            start_image_path: Start frame image (required)
            end_image_path: End frame image (required)
            output_path: Path to save the generated video

        Returns:
            Video data as bytes
        """

        def _sync_generate():
            import time
            from google.genai import types

            # Load start image (now guaranteed to exist)
            start_image = types.Image.from_file(location=str(start_image_path))

            # Load end image (now guaranteed to exist)
            end_image = types.Image.from_file(location=str(end_image_path))

            # Build config with last frame for interpolation
            config = types.GenerateVideosConfig(
                last_frame=end_image,
                duration_seconds=8,
            )

            # Generate video operation with both images
            operation = self.client.models.generate_videos(
                model=self.model_name,
                prompt=prompt,
                image=start_image,
                config=config,
            )

            # Poll the operation status until the video is ready
            while not operation.done:
                logger.debug("waiting_for_video_generation")
                time.sleep(10)
                operation = self.client.operations.get(operation)

            # Download the video
            generated_video = operation.response.generated_videos[0]
            self.client.files.download(file=generated_video.video)
            generated_video.video.save(str(output_path))

        return await asyncio.to_thread(_sync_generate)

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
