"""Nano Banana API client for image generation."""
import asyncio
from pathlib import Path
from typing import Literal, Optional

import structlog
from google import genai

from api_clients.base_client import BaseAPIClient
from config import get_config

logger = structlog.get_logger(__name__)

QualityType = Literal["standard", "hd"]


class NanoBananaClient(BaseAPIClient):
    """Client for Nano Banana image generation API via Gemini."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize the Nano Banana client.

        Args:
            api_key: Google API key (defaults to config)
        """
        config = get_config()
        api_key = api_key or config.google_api_key

        if not api_key:
            raise ValueError("Google API key is required for Nano Banana client")

        super().__init__(api_key=api_key)

        # Create Gemini client
        self.client = genai.Client(api_key=api_key)

        # Use Gemini 2.5 Flash Image model
        self.model_name = "gemini-2.5-flash-image"

    async def generate_and_save_image(
            self,
            prompt: str,
            output_path: Path,
            aspect_ratio: str = "16:9",
            quality: QualityType = "hd",
    ) -> Path:
        """Generate an image from a text prompt.

        Returns:
            Saved path

        Raises:
            Exception: If image generation fails
        """
        try:
            logger.info(
                "generating_image",
                prompt_preview=prompt[:100],
                aspect_ratio=aspect_ratio,
                quality=quality,
            )

            # Generate image using Gemini API
            response = await self._retry_with_backoff(
                self._generate_image_request,
                prompt=prompt,
                output_path=output_path,
            )

            logger.info("image_generated_successfully")
            return response

        except Exception as e:
            logger.error("image_generation_failed", error=str(e), prompt=prompt[:100])
            raise

    async def _generate_image_request(
        self,
        prompt: str,
        output_path: Path
    ):
        """Make the actual image generation request.
        """


        def _sync_generate() -> Path:
            # Generate image using Gemini API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt],
            )

            # Extract image from response parts
            for part in response.parts:
                if part.inline_data is not None:
                    # Convert to PIL image
                    image = part.as_image()
                    image.save(str(output_path))
                    return output_path

            raise ValueError("No image data found in response")

        return await asyncio.to_thread(_sync_generate)


    @staticmethod
    def estimate_cost(num_images: int) -> float:
        """Estimate the cost of generating images.

        Args:
            num_images: Number of images to generate

        Returns:
            Estimated cost in USD
        """
        config = get_config()
        return num_images * config.nano_banana_cost_per_image
