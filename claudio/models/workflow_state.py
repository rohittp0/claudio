"""Workflow state management models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from claudio.models.scene import ScenePlan, VideoRequirements


class WorkflowStatus(str, Enum):
    """Possible workflow states."""

    PLANNING = "planning"
    APPROVAL = "approval"
    GENERATING_IMAGES = "generating_images"
    GENERATING_VIDEOS = "generating_videos"
    CONCATENATING = "concatenating"
    COMPLETED = "completed"
    FAILED = "failed"


class CostEstimate(BaseModel):
    """Cost estimation for video generation."""

    images_cost: float = Field(..., description="Cost for generating images (USD)")
    videos_cost: float = Field(..., description="Cost for generating videos (USD)")
    total_cost: float = Field(..., description="Total estimated cost (USD)")

    def format_cost(self) -> str:
        """Format cost estimate as a string."""
        return (
            f"Images: ${self.images_cost:.2f}\n"
            f"Videos: ${self.videos_cost:.2f}\n"
            f"Total: ${self.total_cost:.2f}"
        )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {"images_cost": 0.50, "videos_cost": 8.00, "total_cost": 8.50}
        }


class ProductionState(BaseModel):
    """Tracks the state of production (image/video generation)."""

    images_generated: list[str] = Field(
        default_factory=list, description="List of scene IDs with images generated"
    )
    videos_generated: list[str] = Field(
        default_factory=list, description="List of scene IDs with videos generated"
    )
    failed_scenes: list[str] = Field(
        default_factory=list, description="List of scene IDs that failed generation"
    )

    def mark_image_generated(self, scene_id: str) -> None:
        """Mark a scene's image as generated."""
        if scene_id not in self.images_generated:
            self.images_generated.append(scene_id)

    def mark_video_generated(self, scene_id: str) -> None:
        """Mark a scene's video as generated."""
        if scene_id not in self.videos_generated:
            self.videos_generated.append(scene_id)

    def mark_scene_failed(self, scene_id: str) -> None:
        """Mark a scene as failed."""
        if scene_id not in self.failed_scenes:
            self.failed_scenes.append(scene_id)

    def is_image_generated(self, scene_id: str) -> bool:
        """Check if a scene's image is generated."""
        return scene_id in self.images_generated

    def is_video_generated(self, scene_id: str) -> bool:
        """Check if a scene's video is generated."""
        return scene_id in self.videos_generated

    def is_scene_failed(self, scene_id: str) -> bool:
        """Check if a scene failed."""
        return scene_id in self.failed_scenes

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "images_generated": ["scene_1", "scene_2"],
                "videos_generated": ["scene_1"],
                "failed_scenes": [],
            }
        }


class AssetPaths(BaseModel):
    """Paths to generated assets."""

    images: dict[str, str] = Field(
        default_factory=dict, description="Mapping of scene_id to image path"
    )
    videos: dict[str, str] = Field(
        default_factory=dict, description="Mapping of scene_id to video path"
    )
    final_video: Optional[str] = Field(default=None, description="Path to final concatenated video")

    def add_image(self, scene_id: str, path: str) -> None:
        """Add an image path."""
        self.images[scene_id] = path

    def add_video(self, scene_id: str, path: str) -> None:
        """Add a video path."""
        self.videos[scene_id] = path

    def get_image(self, scene_id: str) -> Optional[str]:
        """Get image path for a scene."""
        return self.images.get(scene_id)

    def get_video(self, scene_id: str) -> Optional[str]:
        """Get video path for a scene."""
        return self.videos.get(scene_id)

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "images": {"scene_1": "/path/to/scene1_end.png", "scene_2": "/path/to/scene2_end.png"},
                "videos": {"scene_1": "/path/to/scene1.mp4", "scene_2": "/path/to/scene2.mp4"},
                "final_video": "/path/to/final.mp4",
            }
        }


class WorkflowState(BaseModel):
    """Complete workflow state for a video generation session."""

    session_id: str = Field(..., description="Unique session identifier")
    status: WorkflowStatus = Field(..., description="Current workflow status")
    created_at: datetime = Field(default_factory=datetime.now, description="When session was created")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")

    # Requirements and planning
    requirements: Optional[VideoRequirements] = Field(
        default=None, description="User requirements"
    )
    scene_plan: Optional[ScenePlan] = Field(default=None, description="Generated scene plan")

    # Cost estimation
    estimated_cost: Optional[CostEstimate] = Field(
        default=None, description="Estimated generation cost"
    )

    # Production tracking
    production_state: ProductionState = Field(
        default_factory=ProductionState, description="Production progress"
    )
    assets: AssetPaths = Field(default_factory=AssetPaths, description="Generated asset paths")

    # Error tracking
    error_message: Optional[str] = Field(default=None, description="Error message if failed")

    def update_status(self, status: WorkflowStatus) -> None:
        """Update the workflow status."""
        self.status = status
        self.updated_at = datetime.now()

    def mark_failed(self, error_message: str) -> None:
        """Mark the workflow as failed."""
        self.status = WorkflowStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.now()

    def is_complete(self) -> bool:
        """Check if the workflow is complete."""
        return self.status == WorkflowStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if the workflow failed."""
        return self.status == WorkflowStatus.FAILED

    def can_resume(self) -> bool:
        """Check if the workflow can be resumed."""
        return self.status not in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "generating_videos",
                "created_at": "2026-01-10T10:00:00",
                "updated_at": "2026-01-10T10:05:00",
                "requirements": {
                    "business_name": "Joe's Pizza",
                    "video_purpose": "discount advertisement",
                    "duration": 20.0,
                    "theme": "fun, energetic",
                    "quality": "1080p",
                },
                "scene_plan": {"total_duration": 20.0, "quality": "1080p", "scenes": []},
                "estimated_cost": {"images_cost": 0.50, "videos_cost": 8.00, "total_cost": 8.50},
            }
        }
