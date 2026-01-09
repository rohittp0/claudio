"""Production Orchestrator Agent for executing video generation."""

import asyncio
from pathlib import Path
from typing import Any

import structlog

from claudio.mcp_server.tools import (
    concatenate_videos_tool,
    estimate_cost_tool,
    generate_image_tool,
    generate_video_tool,
)
from claudio.models.workflow_state import WorkflowState, WorkflowStatus
from claudio.utils.async_utils import ProgressTracker
from claudio.utils.file_manager import FileManager
from claudio.utils.state_manager import StateManager

logger = structlog.get_logger(__name__)


class ProductionOrchestratorAgent:
    """Agent for orchestrating parallel video production."""

    def __init__(self) -> None:
        """Initialize the Production Orchestrator Agent."""
        pass

    async def estimate_cost(self, state: WorkflowState) -> dict[str, Any]:
        """Estimate the cost of generating the video.

        Args:
            state: Current workflow state

        Returns:
            Cost estimate dictionary
        """
        if not state.scene_plan:
            raise ValueError("No scene plan available for cost estimation")

        num_images = len(state.scene_plan.scenes)
        total_duration = state.scene_plan.total_duration

        logger.info("estimating_cost", num_images=num_images, duration=total_duration)

        result = await estimate_cost_tool(
            num_images=num_images,
            total_video_duration=total_duration,
        )

        if result["success"]:
            from claudio.models.workflow_state import CostEstimate

            state.estimated_cost = CostEstimate(
                images_cost=result["images_cost"],
                videos_cost=result["videos_cost"],
                total_cost=result["total_cost"],
            )
            await StateManager.save_state(state)

        return result

    async def generate_images(self, state: WorkflowState) -> tuple[int, int]:
        """Generate all scene end-frame images in parallel.

        Args:
            state: Current workflow state

        Returns:
            Tuple of (successful_count, failed_count)
        """
        if not state.scene_plan:
            raise ValueError("No scene plan available")

        scenes = state.scene_plan.scenes
        logger.info("generating_images", count=len(scenes))

        # Update status
        state.update_status(WorkflowStatus.GENERATING_IMAGES)
        await StateManager.save_state(state)

        # Create progress tracker
        tracker = ProgressTracker(len(scenes))

        # Generate images in parallel
        tasks = []
        for scene in scenes:
            task = self._generate_scene_image(state, scene, tracker)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = len(results) - successful

        logger.info(
            "images_generation_complete",
            successful=successful,
            failed=failed,
            total=len(scenes),
        )

        return successful, failed

    async def _generate_scene_image(
        self, state: WorkflowState, scene: Any, tracker: ProgressTracker
    ) -> dict[str, Any]:
        """Generate image for a single scene.

        Args:
            state: Current workflow state
            scene: Scene to generate image for
            tracker: Progress tracker

        Returns:
            Result dictionary from generate_image_tool
        """
        try:
            # Generate image
            result = await generate_image_tool(
                session_id=state.session_id,
                scene_id=scene.scene_id,
                prompt=scene.end_image_prompt,
                aspect_ratio="16:9",
                quality="hd",
            )

            if result["success"]:
                # Update scene and state
                scene.image_generated = True
                scene.image_path = result["image_path"]
                state.production_state.mark_image_generated(scene.scene_id)
                state.assets.add_image(scene.scene_id, result["image_path"])
                await StateManager.save_state(state)
                await tracker.mark_completed()

                logger.info("scene_image_generated", scene_id=scene.scene_id)
            else:
                state.production_state.mark_scene_failed(scene.scene_id)
                await tracker.mark_failed()
                logger.error(
                    "scene_image_failed",
                    scene_id=scene.scene_id,
                    error=result.get("error"),
                )

            return result

        except Exception as e:
            logger.error("scene_image_exception", scene_id=scene.scene_id, error=str(e))
            state.production_state.mark_scene_failed(scene.scene_id)
            await tracker.mark_failed()
            return {"success": False, "error": str(e)}

    async def generate_videos(self, state: WorkflowState) -> tuple[int, int]:
        """Generate all scene videos in parallel.

        Args:
            state: Current workflow state

        Returns:
            Tuple of (successful_count, failed_count)
        """
        if not state.scene_plan:
            raise ValueError("No scene plan available")

        scenes = state.scene_plan.scenes
        logger.info("generating_videos", count=len(scenes))

        # Update status
        state.update_status(WorkflowStatus.GENERATING_VIDEOS)
        await StateManager.save_state(state)

        # Create progress tracker
        tracker = ProgressTracker(len(scenes))

        # Generate videos in parallel
        tasks = []
        for i, scene in enumerate(scenes):
            # Get previous scene's end image for continuity (except first scene)
            prev_image_path = None
            if i > 0:
                prev_scene = scenes[i - 1]
                prev_image_path = prev_scene.image_path

            task = self._generate_scene_video(state, scene, prev_image_path, tracker)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = len(results) - successful

        logger.info(
            "videos_generation_complete",
            successful=successful,
            failed=failed,
            total=len(scenes),
        )

        return successful, failed

    async def _generate_scene_video(
        self,
        state: WorkflowState,
        scene: Any,
        prev_image_path: str | None,
        tracker: ProgressTracker,
    ) -> dict[str, Any]:
        """Generate video for a single scene.

        Args:
            state: Current workflow state
            scene: Scene to generate video for
            prev_image_path: Path to previous scene's end image (for continuity)
            tracker: Progress tracker

        Returns:
            Result dictionary from generate_video_tool
        """
        try:
            # Ensure image is generated first
            if not scene.image_generated or not scene.image_path:
                raise ValueError(f"Image not generated for scene {scene.scene_id}")

            # Generate video
            result = await generate_video_tool(
                session_id=state.session_id,
                scene_id=scene.scene_id,
                prompt=scene.video_prompt,
                duration=scene.duration,
                end_image_path=scene.image_path,
                start_image_path=prev_image_path,
                resolution=state.scene_plan.quality if state.scene_plan else "1080p",
            )

            if result["success"]:
                # Update scene and state
                scene.video_generated = True
                scene.video_path = result["video_path"]
                state.production_state.mark_video_generated(scene.scene_id)
                state.assets.add_video(scene.scene_id, result["video_path"])
                await StateManager.save_state(state)
                await tracker.mark_completed()

                logger.info("scene_video_generated", scene_id=scene.scene_id)
            else:
                state.production_state.mark_scene_failed(scene.scene_id)
                await tracker.mark_failed()
                logger.error(
                    "scene_video_failed",
                    scene_id=scene.scene_id,
                    error=result.get("error"),
                )

            return result

        except Exception as e:
            logger.error("scene_video_exception", scene_id=scene.scene_id, error=str(e))
            state.production_state.mark_scene_failed(scene.scene_id)
            await tracker.mark_failed()
            return {"success": False, "error": str(e)}

    async def concatenate_videos(self, state: WorkflowState) -> dict[str, Any]:
        """Concatenate all scene videos into final video.

        Args:
            state: Current workflow state

        Returns:
            Result dictionary from concatenate_videos_tool
        """
        if not state.scene_plan:
            raise ValueError("No scene plan available")

        logger.info("concatenating_videos", session_id=state.session_id)

        # Update status
        state.update_status(WorkflowStatus.CONCATENATING)
        await StateManager.save_state(state)

        # Get video paths in order
        video_paths = []
        for scene in state.scene_plan.scenes:
            if scene.video_path:
                video_paths.append(scene.video_path)
            else:
                logger.warning("missing_video_path", scene_id=scene.scene_id)

        if not video_paths:
            raise ValueError("No videos available for concatenation")

        # Concatenate
        result = await concatenate_videos_tool(
            session_id=state.session_id,
            video_paths=video_paths,
        )

        if result["success"]:
            state.assets.final_video = result["final_video_path"]
            state.update_status(WorkflowStatus.COMPLETED)
            await StateManager.save_state(state)
            logger.info("concatenation_complete", path=result["final_video_path"])

        return result

    async def execute_full_production(
        self,
        state: WorkflowState,
        progress_callback: Any = None,
    ) -> WorkflowState:
        """Execute the full production workflow.

        Args:
            state: Current workflow state
            progress_callback: Optional callback for progress updates

        Returns:
            Updated workflow state
        """
        try:
            logger.info("starting_full_production", session_id=state.session_id)

            # Phase 1: Generate images
            if progress_callback:
                await progress_callback("Generating scene end-frame images...")

            img_success, img_failed = await self.generate_images(state)

            if img_failed > 0:
                logger.warning("some_images_failed", failed=img_failed)

            if img_success == 0:
                raise ValueError("No images were generated successfully")

            # Phase 2: Generate videos
            if progress_callback:
                await progress_callback("Generating video segments...")

            vid_success, vid_failed = await self.generate_videos(state)

            if vid_failed > 0:
                logger.warning("some_videos_failed", failed=vid_failed)

            if vid_success == 0:
                raise ValueError("No videos were generated successfully")

            # Phase 3: Concatenate videos
            if progress_callback:
                await progress_callback("Combining video segments...")

            result = await self.concatenate_videos(state)

            if not result["success"]:
                raise ValueError(f"Concatenation failed: {result.get('error')}")

            logger.info("production_complete", session_id=state.session_id)

            return state

        except Exception as e:
            logger.error("production_failed", error=str(e))
            state.mark_failed(str(e))
            await StateManager.save_state(state)
            raise
