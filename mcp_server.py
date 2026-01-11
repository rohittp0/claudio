#!/usr/bin/env python3
"""MCP server for Claudio video generation tools.

This server exposes video generation tools to Claude Code CLI via the Model Context Protocol.
Claude acts as the director agent, using these tools to create professional videos.
"""

import uuid
from typing import Any

from mcp.server.fastmcp import FastMCP

from tools.tools import (
    concatenate_videos_tool,
    estimate_cost_tool,
    generate_image_tool,
    generate_video_tool,
    load_state_tool,
    save_state_tool,
)

# Create FastMCP server
server = FastMCP(
    "video-director",
    instructions="""AI-powered video generation server using Google Veo 3.1 and Imagen.

This server provides tools for creating professional videos through:
1. Scene planning and cost estimation
2. End-frame image generation (Imagen via Nano Banana)
3. Video segment generation (Veo 3.1 - fixed 8-second segments)
4. Video concatenation using FFmpeg
5. Workflow state management

Key Constraints:
- Veo 3.1 generates fixed 8-second video segments
- For longer videos, create multiple scenes
- Each scene needs an end-frame image first
- Previous scene's end-frame becomes next scene's start-frame for continuity
"""
)


@server.tool()
async def generate_image(
    session_id: str,
    scene_id: str,
    prompt: str,
    aspect_ratio: str = "16:9",
    quality: str = "hd",
) -> dict[str, Any]:
    """Generate an end-frame image for a video scene using Imagen (Nano Banana).

    The generated image will be used as the final frame of the video segment.
    For continuity, it can also be used as the start frame of the next scene.

    Args:
        session_id: Unique session identifier (use UUID format)
        scene_id: Scene identifier (e.g., "scene_1", "scene_2")
        prompt: Detailed description of the image to generate
        aspect_ratio: Image aspect ratio (default: "16:9")
        quality: Image quality - "hd" or "standard" (default: "hd")

    Returns:
        Dictionary with success status, image_path, and scene_id
    """
    return await generate_image_tool(
        session_id=session_id,
        scene_id=scene_id,
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        quality=quality,
    )


@server.tool()
async def generate_video(
    session_id: str,
    scene_id: str,
    prompt: str,
    end_image_path: str,
    start_image_path: str | None = None,
) -> dict[str, Any]:
    """Generate an 8-second video segment using Veo 3.1.

    Veo 3.1 always generates exactly 8 seconds of video. The video will end at
    the exact frame shown in end_image_path. Optionally provide start_image_path
    for smooth transitions between scenes.

    Args:
        session_id: Unique session identifier (same as used for images)
        scene_id: Scene identifier (same as used for the end image)
        prompt: Detailed description of what happens in this 8-second scene
        end_image_path: Absolute path to the end-frame image (required)
        start_image_path: Optional path to start-frame image for continuity

    Returns:
        Dictionary with success status, video_path, and scene_id
    """
    return await generate_video_tool(
        session_id=session_id,
        scene_id=scene_id,
        prompt=prompt,
        end_image_path=end_image_path,
        start_image_path=start_image_path,
    )


@server.tool()
async def concatenate_videos(
    session_id: str,
    video_paths: list[str],
) -> dict[str, Any]:
    """Concatenate multiple video segments into a final video using FFmpeg.

    Combines video segments in the order provided. All videos should be from
    the same session and have consistent format (resolution, codec).

    Args:
        session_id: Session identifier (same as used for generation)
        video_paths: List of absolute paths to video files, in order

    Returns:
        Dictionary with success status and final_video_path
    """
    return await concatenate_videos_tool(
        session_id=session_id,
        video_paths=video_paths,
    )


@server.tool()
async def estimate_cost(
    num_images: int,
    total_video_duration: float,
) -> dict[str, Any]:
    """Estimate the cost of generating images and videos.

    Provides cost breakdown before starting generation. Useful for getting
    user approval before expensive operations.

    Pricing (approximate):
    - Images: $0.10 per image
    - Videos: $0.40 per second

    Args:
        num_images: Number of end-frame images to generate
        total_video_duration: Total video duration in seconds

    Returns:
        Dictionary with images_cost, videos_cost, total_cost, and formatted string
    """
    return await estimate_cost_tool(
        num_images=num_images,
        total_video_duration=total_video_duration,
    )


@server.tool()
async def save_workflow_state(
    state_json: str,
) -> dict[str, Any]:
    """Save workflow state to disk for resuming later.

    Persists the current workflow state including scene plan, generated assets,
    and progress. Useful for long-running workflows that may be interrupted.

    Args:
        state_json: JSON string representation of WorkflowState

    Returns:
        Dictionary with success status and session_id
    """
    return await save_state_tool(state_json=state_json)


@server.tool()
async def load_workflow_state(
    session_id: str,
) -> dict[str, Any]:
    """Load a previously saved workflow state from disk.

    Retrieves workflow state to resume an interrupted session or review
    past generations.

    Args:
        session_id: The session identifier to load

    Returns:
        Dictionary with success status and state data (or error)
    """
    return await load_state_tool(session_id=session_id)


@server.tool()
async def create_session_id() -> dict[str, Any]:
    """Generate a new unique session ID for a video generation workflow.

    Creates a UUID-based session identifier to track assets and state
    throughout the video generation process.

    Returns:
        Dictionary with success status and generated session_id
    """
    try:
        session_id = str(uuid.uuid4())
        return {
            "success": True,
            "session_id": session_id,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def main():
    """Run the MCP server on stdio for Claude Code CLI integration."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
