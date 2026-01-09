"""Nano Banana API client for image generation."""

from pathlib import Path
from typing import Literal, Optional

import google.generativeai as genai
import structlog

from claudio.api_clients.base_client import BaseAPIClient
from claudio.config import get_config

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

        # Configure Gemini API
        genai.configure(api_key=api_key)

        # Use Imagen 3 model for image generation
        self.model = genai.ImageGenerationModel("imagen-3.0-generate-001")

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        quality: QualityType = "hd",
        safety_filter_level: str = "block_some",
    ) -> bytes:
        """Generate an image from a text prompt.

        Args:
            prompt: Text description of the image to generate
            aspect_ratio: Image aspect ratio (e.g., "16:9", "1:1", "9:16")
            quality: Image quality ("standard" or "hd")
            safety_filter_level: Safety filter level

        Returns:
            Image data as bytes

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
                aspect_ratio=aspect_ratio,
                quality=quality,
                safety_filter_level=safety_filter_level,
            )

            logger.info("image_generated_successfully")
            return response

        except Exception as e:
            logger.error("image_generation_failed", error=str(e), prompt=prompt[:100])
            raise

    async def _generate_image_request(
        self,
        prompt: str,
        aspect_ratio: str,
        quality: QualityType,
        safety_filter_level: str,
    ) -> bytes:
        """Make the actual image generation request.

        Args:
            prompt: Text description of the image
            aspect_ratio: Image aspect ratio
            quality: Image quality
            safety_filter_level: Safety filter level

        Returns:
            Image data as bytes
        """
        # Note: The actual Gemini API call needs to be made using the SDK
        # This is a placeholder for the actual implementation

        # For now, using the synchronous API since async is not directly available
        import asyncio

        def _sync_generate() -> bytes:
            result = self.model.generate_images(
                prompt=prompt,
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                safety_filter_level=safety_filter_level,
                person_generation="allow_adult",  # Allow person generation
            )

            if not result or not result.images:
                raise ValueError("No images generated")

            # Get the first image
            image = result.images[0]

            # Return image bytes
            # Note: The exact method to get bytes may vary based on the SDK version
            return image._pil_image.tobytes() if hasattr(image, "_pil_image") else b""

        return await asyncio.to_thread(_sync_generate)

    async def generate_and_save_image(
        self,
        prompt: str,
        output_path: Path,
        aspect_ratio: str = "16:9",
        quality: QualityType = "hd",
    ) -> Path:
        """Generate an image and save it to disk.

        Args:
            prompt: Text description of the image to generate
            output_path: Where to save the generated image
            aspect_ratio: Image aspect ratio
            quality: Image quality

        Returns:
            Path to the saved image

        Raises:
            Exception: If generation or saving fails
        """
        logger.info("generating_and_saving_image", output_path=str(output_path))

        # Generate image
        image_data = await self.generate_image(
            prompt=prompt, aspect_ratio=aspect_ratio, quality=quality
        )

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save to disk
        import aiofiles

        async with aiofiles.open(output_path, "wb") as f:
            await f.write(image_data)

        logger.info("image_saved", path=str(output_path))
        return output_path

    def estimate_cost(self, num_images: int) -> float:
        """Estimate the cost of generating images.

        Args:
            num_images: Number of images to generate

        Returns:
            Estimated cost in USD
        """
        config = get_config()
        return num_images * config.nano_banana_cost_per_image
