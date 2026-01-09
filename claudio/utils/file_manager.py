"""File management utilities for handling assets."""

import shutil
from pathlib import Path
from typing import Optional

import aiofiles

from claudio.config import get_session_dir, get_session_images_dir, get_session_videos_dir


class FileManager:
    """Manages file operations for video generation assets."""

    @staticmethod
    def get_image_path(session_id: str, scene_id: str) -> Path:
        """Get the path for a scene's end image.

        Args:
            session_id: The session identifier
            scene_id: The scene identifier

        Returns:
            Path where the image should be saved
        """
        images_dir = get_session_images_dir(session_id)
        return images_dir / f"{scene_id}_end.png"

    @staticmethod
    def get_video_path(session_id: str, scene_id: str) -> Path:
        """Get the path for a scene's video.

        Args:
            session_id: The session identifier
            scene_id: The scene identifier

        Returns:
            Path where the video should be saved
        """
        videos_dir = get_session_videos_dir(session_id)
        return videos_dir / f"{scene_id}.mp4"

    @staticmethod
    def get_final_video_path(session_id: str) -> Path:
        """Get the path for the final concatenated video.

        Args:
            session_id: The session identifier

        Returns:
            Path where the final video should be saved
        """
        session_dir = get_session_dir(session_id)
        return session_dir / "final_video.mp4"

    @staticmethod
    async def save_image(session_id: str, scene_id: str, image_data: bytes) -> Path:
        """Save image data to disk.

        Args:
            session_id: The session identifier
            scene_id: The scene identifier
            image_data: The image binary data

        Returns:
            Path where the image was saved
        """
        image_path = FileManager.get_image_path(session_id, scene_id)

        async with aiofiles.open(image_path, "wb") as f:
            await f.write(image_data)

        return image_path

    @staticmethod
    async def save_video(session_id: str, scene_id: str, video_data: bytes) -> Path:
        """Save video data to disk.

        Args:
            session_id: The session identifier
            scene_id: The scene identifier
            video_data: The video binary data

        Returns:
            Path where the video was saved
        """
        video_path = FileManager.get_video_path(session_id, scene_id)

        async with aiofiles.open(video_path, "wb") as f:
            await f.write(video_data)

        return video_path

    @staticmethod
    async def copy_file(source: Path, destination: Path) -> None:
        """Copy a file from source to destination.

        Args:
            source: Source file path
            destination: Destination file path
        """
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    @staticmethod
    def image_exists(session_id: str, scene_id: str) -> bool:
        """Check if an image exists for a scene.

        Args:
            session_id: The session identifier
            scene_id: The scene identifier

        Returns:
            True if image exists, False otherwise
        """
        image_path = FileManager.get_image_path(session_id, scene_id)
        return image_path.exists()

    @staticmethod
    def video_exists(session_id: str, scene_id: str) -> bool:
        """Check if a video exists for a scene.

        Args:
            session_id: The session identifier
            scene_id: The scene identifier

        Returns:
            True if video exists, False otherwise
        """
        video_path = FileManager.get_video_path(session_id, scene_id)
        return video_path.exists()

    @staticmethod
    def final_video_exists(session_id: str) -> bool:
        """Check if the final video exists.

        Args:
            session_id: The session identifier

        Returns:
            True if final video exists, False otherwise
        """
        final_path = FileManager.get_final_video_path(session_id)
        return final_path.exists()

    @staticmethod
    def cleanup_session(session_id: str, keep_final: bool = True) -> None:
        """Clean up session files.

        Args:
            session_id: The session identifier
            keep_final: If True, keep the final video and state file
        """
        session_dir = get_session_dir(session_id)

        if not session_dir.exists():
            return

        if keep_final:
            # Delete only intermediate files
            images_dir = get_session_images_dir(session_id)
            videos_dir = get_session_videos_dir(session_id)

            if images_dir.exists():
                shutil.rmtree(images_dir)
            if videos_dir.exists():
                shutil.rmtree(videos_dir)
        else:
            # Delete entire session directory
            shutil.rmtree(session_dir)

    @staticmethod
    def get_file_size(file_path: Path) -> int:
        """Get file size in bytes.

        Args:
            file_path: Path to the file

        Returns:
            File size in bytes, or 0 if file doesn't exist
        """
        if not file_path.exists():
            return 0
        return file_path.stat().st_size

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size in human-readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted string (e.g., "1.5 MB")
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
