"""MCP tool definitions and handlers for video generation."""

import asyncio
from pathlib import Path
from typing import Any, Optional

import ffmpeg
import structlog

from claudio.api_clients.nano_banana_client import NanoBananaClient
from claudio.api_clients.veo_client import VeoClient
from claudio.config import get_config
from claudio.models.workflow_state import CostEstimate
from claudio.utils.file_manager import FileManager
from claudio.utils.state_manager import StateManager

logger = structlog.get_logger(__name__)


async def generate_image_tool(
    session_id: str,
    scene_id: str,
    prompt: str,
    aspect_ratio: str = "16:9",
    quality: str = "hd",
) -> dict[str, Any]:
    """Generate an image using Nano Banana API.

    Args:
        session_id: The session identifier
        scene_id: The scene identifier
        prompt: Text description of the image
        aspect_ratio: Image aspect ratio (default: "16:9")
        quality: Image quality (default: "hd")

    Returns:
        Dictionary with image path and success status
    """
    try:
        logger.info("tool.generate_image", session_id=session_id, scene_id=scene_id)

        # Initialize client
        client = NanoBananaClient()

        # Get output path
        output_path = FileManager.get_image_path(session_id, scene_id)

        # Generate and save image
        saved_path = await client.generate_and_save_image(
            prompt=prompt,
            output_path=output_path,
            aspect_ratio=aspect_ratio,
            quality=quality,  # type: ignore
        )

        logger.info("tool.generate_image.success", path=str(saved_path))

        return {
            "success": True,
            "image_path": str(saved_path),
            "scene_id": scene_id,
        }

    except Exception as e:
        logger.error("tool.generate_image.failed", error=str(e), scene_id=scene_id)
        return {
            "success": False,
            "error": str(e),
            "scene_id": scene_id,
        }


async def generate_video_tool(
    session_id: str,
    scene_id: str,
    prompt: str,
    duration: float,
    end_image_path: str,
    start_image_path: Optional[str] = None,
    resolution: str = "1080p",
) -> dict[str, Any]:
    """Generate a video using Veo 3 API.

    Args:
        session_id: The session identifier
        scene_id: The scene identifier
        prompt: Text description of the video
        duration: Video duration in seconds (max 8)
        end_image_path: Path to image for the last frame
        start_image_path: Optional path to image for the first frame
        resolution: Video resolution (default: "1080p")

    Returns:
        Dictionary with video path and success status
    """
    try:
        logger.info("tool.generate_video", session_id=session_id, scene_id=scene_id)

        # Initialize client
        client = VeoClient()

        # Get output path
        output_path = FileManager.get_video_path(session_id, scene_id)

        # Convert string paths to Path objects
        end_image = Path(end_image_path) if end_image_path else None
        start_image = Path(start_image_path) if start_image_path else None

        # Generate and save video
        saved_path = await client.generate_and_save_video(
            prompt=prompt,
            duration=duration,
            output_path=output_path,
            end_image_path=end_image,
            start_image_path=start_image,
            resolution=resolution,  # type: ignore
        )

        logger.info("tool.generate_video.success", path=str(saved_path))

        return {
            "success": True,
            "video_path": str(saved_path),
            "scene_id": scene_id,
        }

    except Exception as e:
        logger.error("tool.generate_video.failed", error=str(e), scene_id=scene_id)
        return {
            "success": False,
            "error": str(e),
            "scene_id": scene_id,
        }


async def concatenate_videos_tool(
    session_id: str,
    video_paths: list[str],
) -> dict[str, Any]:
    """Concatenate video segments using ffmpeg.

    Args:
        session_id: The session identifier
        video_paths: List of video file paths in order

    Returns:
        Dictionary with final video path and success status
    """
    try:
        logger.info("tool.concatenate_videos", session_id=session_id, count=len(video_paths))

        # Get output path
        output_path = FileManager.get_final_video_path(session_id)

        # Create a temporary file list for ffmpeg
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            for video_path in video_paths:
                # Write in ffmpeg concat format
                f.write(f"file '{video_path}'\n")
            list_file = f.name

        try:
            # Run ffmpeg concatenation
            await asyncio.to_thread(
                lambda: (
                    ffmpeg.input(list_file, format="concat", safe=0)
                    .output(
                        str(output_path),
                        c="copy",  # Copy codec (no re-encoding)
                        loglevel="error",
                    )
                    .overwrite_output()
                    .run()
                )
            )

            logger.info("tool.concatenate_videos.success", output_path=str(output_path))

            return {
                "success": True,
                "final_video_path": str(output_path),
            }

        finally:
            # Clean up temporary file
            Path(list_file).unlink(missing_ok=True)

    except Exception as e:
        logger.error("tool.concatenate_videos.failed", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


async def estimate_cost_tool(
    num_images: int,
    total_video_duration: float,
) -> dict[str, Any]:
    """Estimate the cost of generating videos.

    Args:
        num_images: Number of images to generate
        total_video_duration: Total video duration in seconds

    Returns:
        Dictionary with cost breakdown
    """
    try:
        logger.info(
            "tool.estimate_cost",
            num_images=num_images,
            total_duration=total_video_duration,
        )

        # Initialize clients for cost calculation
        image_client = NanoBananaClient()
        video_client = VeoClient()

        # Calculate costs
        images_cost = image_client.estimate_cost(num_images)
        videos_cost = video_client.estimate_cost(total_video_duration)
        total_cost = images_cost + videos_cost

        estimate = CostEstimate(
            images_cost=images_cost,
            videos_cost=videos_cost,
            total_cost=total_cost,
        )

        logger.info("tool.estimate_cost.success", total_cost=total_cost)

        return {
            "success": True,
            "images_cost": images_cost,
            "videos_cost": videos_cost,
            "total_cost": total_cost,
            "formatted": estimate.format_cost(),
        }

    except Exception as e:
        logger.error("tool.estimate_cost.failed", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


async def save_state_tool(
    state_json: str,
) -> dict[str, Any]:
    """Save workflow state to disk.

    Args:
        state_json: JSON string of the workflow state

    Returns:
        Dictionary with success status
    """
    try:
        import json

        from claudio.models.workflow_state import WorkflowState

        # Parse JSON
        state_dict = json.loads(state_json)
        state = WorkflowState(**state_dict)

        # Save state
        await StateManager.save_state(state)

        logger.info("tool.save_state.success", session_id=state.session_id)

        return {
            "success": True,
            "session_id": state.session_id,
        }

    except Exception as e:
        logger.error("tool.save_state.failed", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


async def load_state_tool(
    session_id: str,
) -> dict[str, Any]:
    """Load workflow state from disk.

    Args:
        session_id: The session identifier

    Returns:
        Dictionary with state data or error
    """
    try:
        # Load state
        state = await StateManager.load_state(session_id)

        if not state:
            return {
                "success": False,
                "error": f"State not found for session {session_id}",
            }

        logger.info("tool.load_state.success", session_id=session_id)

        # Convert to dict
        state_dict = state.model_dump(mode="json")

        return {
            "success": True,
            "state": state_dict,
        }

    except Exception as e:
        logger.error("tool.load_state.failed", error=str(e), session_id=session_id)
        return {
            "success": False,
            "error": str(e),
        }


# Tool definitions for MCP server
TOOLS = [
    {
        "name": "generate_image",
        "description": "Generate an image using Nano Banana API for scene end-frames",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session identifier"},
                "scene_id": {"type": "string", "description": "Scene identifier"},
                "prompt": {"type": "string", "description": "Image description prompt"},
                "aspect_ratio": {
                    "type": "string",
                    "description": "Image aspect ratio",
                    "default": "16:9",
                },
                "quality": {
                    "type": "string",
                    "description": "Image quality (standard or hd)",
                    "default": "hd",
                },
            },
            "required": ["session_id", "scene_id", "prompt"],
        },
        "handler": generate_image_tool,
    },
    {
        "name": "generate_video",
        "description": "Generate a video segment using Veo 3 API with image constraints",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session identifier"},
                "scene_id": {"type": "string", "description": "Scene identifier"},
                "prompt": {"type": "string", "description": "Video description prompt"},
                "duration": {"type": "number", "description": "Video duration in seconds (max 8)"},
                "end_image_path": {"type": "string", "description": "Path to end-frame image"},
                "start_image_path": {
                    "type": "string",
                    "description": "Optional path to start-frame image",
                },
                "resolution": {
                    "type": "string",
                    "description": "Video resolution (720p or 1080p)",
                    "default": "1080p",
                },
            },
            "required": ["session_id", "scene_id", "prompt", "duration", "end_image_path"],
        },
        "handler": generate_video_tool,
    },
    {
        "name": "concatenate_videos",
        "description": "Concatenate video segments into a final video using ffmpeg",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session identifier"},
                "video_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of video file paths in order",
                },
            },
            "required": ["session_id", "video_paths"],
        },
        "handler": concatenate_videos_tool,
    },
    {
        "name": "estimate_cost",
        "description": "Estimate the cost of generating images and videos",
        "inputSchema": {
            "type": "object",
            "properties": {
                "num_images": {
                    "type": "integer",
                    "description": "Number of images to generate",
                },
                "total_video_duration": {
                    "type": "number",
                    "description": "Total video duration in seconds",
                },
            },
            "required": ["num_images", "total_video_duration"],
        },
        "handler": estimate_cost_tool,
    },
    {
        "name": "save_state",
        "description": "Save workflow state to disk",
        "inputSchema": {
            "type": "object",
            "properties": {
                "state_json": {
                    "type": "string",
                    "description": "JSON string of the workflow state",
                },
            },
            "required": ["state_json"],
        },
        "handler": save_state_tool,
    },
    {
        "name": "load_state",
        "description": "Load workflow state from disk",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session identifier"},
            },
            "required": ["session_id"],
        },
        "handler": load_state_tool,
    },
]
