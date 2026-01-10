"""Configuration management for Claudio."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()


class Config(BaseModel):
    """Application configuration."""

    # API Keys
    anthropic_api_key: str = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    google_api_key: str = Field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))

    # Optional Google Cloud settings (for Vertex AI)
    google_cloud_project: Optional[str] = Field(
        default_factory=lambda: os.getenv("GOOGLE_CLOUD_PROJECT")
    )
    google_cloud_location: str = Field(
        default_factory=lambda: os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    )

    # Workspace Configuration
    workspace_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("WORKSPACE_DIR", "~/.claudio")).expanduser()
    )
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # Cost Estimation (USD)
    nano_banana_cost_per_image: float = Field(
        default_factory=lambda: float(os.getenv("NANO_BANANA_COST_PER_IMAGE", "0.10"))
    )
    veo_cost_per_second: float = Field(
        default_factory=lambda: float(os.getenv("VEO_COST_PER_SECOND", "0.40"))
    )

    # Video Generation Defaults
    max_scene_duration: int = Field(
        default_factory=lambda: int(os.getenv("MAX_SCENE_DURATION", "8"))
    )

    def validate_api_keys(self) -> None:
        """Validate that required API keys are present."""
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required in .env file")
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required in .env file")

    def ensure_workspace_dirs(self) -> None:
        """Ensure workspace directories exist."""
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        sessions_dir = self.workspace_dir / "sessions"
        sessions_dir.mkdir(exist_ok=True)

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True


# Global config instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config


def get_session_dir(session_id: str) -> Path:
    """Get the directory for a specific session.

    Args:
        session_id: The session identifier

    Returns:
        Path to the session directory
    """
    session_dir = config.workspace_dir / "sessions" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (session_dir / "images").mkdir(exist_ok=True)
    (session_dir / "videos").mkdir(exist_ok=True)

    return session_dir


def get_session_images_dir(session_id: str) -> Path:
    """Get the images directory for a session."""
    return get_session_dir(session_id) / "images"


def get_session_videos_dir(session_id: str) -> Path:
    """Get the videos directory for a session."""
    return get_session_dir(session_id) / "videos"


def get_session_state_file(session_id: str) -> Path:
    """Get the state file path for a session."""
    return get_session_dir(session_id) / "state.json"
