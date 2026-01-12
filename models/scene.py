"""Scene data models."""

from typing import Optional

from pydantic import BaseModel, Field


class Scene(BaseModel):
    """Represents a single scene in the video."""

    scene_id: str = Field(..., description="Unique identifier for the scene (e.g., 'scene_1')")
    duration: float = Field(..., gt=0, le=8, description="Duration in seconds (max 8 for Veo API)")
    video_prompt: str = Field(..., description="Detailed prompt for video generation")
    end_image_prompt: str = Field(..., description="Prompt for generating the end-frame image")
    start_image_prompt: Optional[str] = Field(default=None, description="Prompt for generating the start-frame image (first scene only)")

    # Production tracking
    image_generated: bool = Field(default=False, description="Whether end image has been generated")
    video_generated: bool = Field(default=False, description="Whether video has been generated")
    image_path: Optional[str] = Field(default=None, description="Path to generated end image")
    video_path: Optional[str] = Field(default=None, description="Path to generated video")
    start_image_path: Optional[str] = Field(default=None, description="Path to generated start image (first scene only)")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "scene_id": "scene_1",
                "duration": 5.0,
                "video_prompt": "Camera slowly zooms into vibrant storefront of Joe's Pizza with neon sign glowing at dusk",
                "end_image_prompt": "Storefront of Joe's Pizza with bright red neon sign, warm lighting, inviting atmosphere, photorealistic",
                "image_generated": False,
                "video_generated": False,
            }
        }


class ScenePlan(BaseModel):
    """Complete scene plan for a video."""

    total_duration: float = Field(..., gt=0, description="Total video duration in seconds")
    theme: Optional[str] = Field(default=None, description="Overall theme/style of the video")
    scenes: list[Scene] = Field(..., min_length=1, description="List of scenes in order")

    def get_scene_by_id(self, scene_id: str) -> Optional[Scene]:
        """Get a scene by its ID.

        Args:
            scene_id: The scene identifier

        Returns:
            The scene if found, None otherwise
        """
        for scene in self.scenes:
            if scene.scene_id == scene_id:
                return scene
        return None

    def get_scene_count(self) -> int:
        """Get the total number of scenes."""
        return len(self.scenes)

    def get_completed_scenes_count(self) -> int:
        """Get the number of scenes with both image and video generated."""
        return sum(1 for scene in self.scenes if scene.image_generated and scene.video_generated)

    def is_complete(self) -> bool:
        """Check if all scenes are generated."""
        return all(scene.image_generated and scene.video_generated for scene in self.scenes)

    def get_next_scene_for_image(self) -> Optional[Scene]:
        """Get the next scene that needs image generation."""
        for scene in self.scenes:
            if not scene.image_generated:
                return scene
        return None

    def get_next_scene_for_video(self) -> Optional[Scene]:
        """Get the next scene that needs video generation."""
        for scene in self.scenes:
            if scene.image_generated and not scene.video_generated:
                return scene
        return None

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "total_duration": 20.0,
                "theme": "vibrant, energetic, fun",
                "scenes": [
                    {
                        "scene_id": "scene_1",
                        "duration": 5.0,
                        "video_prompt": "Camera zooms into storefront",
                        "end_image_prompt": "Storefront with neon sign",
                    },
                    {
                        "scene_id": "scene_2",
                        "duration": 5.0,
                        "video_prompt": "Pizza being prepared",
                        "end_image_prompt": "Fresh pizza with toppings",
                    },
                ],
            }
        }


class VideoRequirements(BaseModel):
    """User requirements for video generation."""

    business_name: Optional[str] = Field(default=None, description="Name of business/product")
    video_purpose: str = Field(..., description="Purpose of the video (e.g., advertisement, tutorial)")
    duration: float = Field(..., gt=0, description="Desired video duration in seconds")
    theme: Optional[str] = Field(default=None, description="Theme/style (e.g., fun, professional)")
    additional_context: Optional[str] = Field(
        default=None, description="Any additional context or requirements"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "business_name": "Joe's Pizza",
                "video_purpose": "20% discount advertisement",
                "duration": 20.0,
                "theme": "fun, family-friendly, energetic",
                "additional_context": "Emphasize the quality of ingredients",
            }
        }
