"""Scene Planning Agent for conversational requirements gathering and scene creation."""

import json
import math
import uuid
from typing import Any

from anthropic import Anthropic
import structlog

from config import get_config
from models.scene import Scene, ScenePlan, VideoRequirements
from models.workflow_state import WorkflowState, WorkflowStatus

logger = structlog.get_logger(__name__)


class ScenePlanningAgent:
    """Agent for gathering requirements and creating scene plans."""

    def __init__(self) -> None:
        """Initialize the Scene Planning Agent."""
        config = get_config()
        self.client = Anthropic(api_key=config.anthropic_api_key)
        self.model = "claude-sonnet-4-5-20250929"

    def create_planning_prompt(self, user_request: str) -> str:
        """Create the system prompt for scene planning.

        Args:
            user_request: The user's initial video request

        Returns:
            System prompt for the planning conversation
        """
        return f"""You are a professional video director assistant. Your role is to help users create detailed video plans.

The user has requested: "{user_request}"

Your task is to gather the following information through a natural conversation:
1. Business/product name (if applicable)
2. Desired video duration in seconds
3. Theme and style (e.g., fun, professional, energetic)
4. Any additional context or requirements

Important constraints:
- Veo 3.1 generates fixed 8-second video segments
- Each scene must be 8 seconds or less in duration
- For videos longer than 8 seconds, create multiple scenes (e.g., 25-second video = 4 scenes: 8s + 8s + 8s + 1s)
- Each scene needs a detailed video prompt and an end-image prompt
- The end image of one scene becomes the start image of the next (for continuity)
- Plan for smooth narrative flow across scenes

After gathering requirements, create a detailed scene plan with:
- Scene-by-scene breakdown
- Duration for each scene (max 8 seconds)
- Detailed video prompt for each scene
- Detailed end-image description for each scene

Ask questions one at a time to keep the conversation natural. Once you have all information, present a complete scene plan for approval.

Output format for the final scene plan:
```json
{{
  "requirements": {{
    "business_name": "...",
    "video_purpose": "...",
    "duration": <total_seconds>,
    "theme": "..."
  }},
  "scenes": [
    {{
      "scene_id": "scene_1",
      "duration": <seconds_max_8>,
      "video_prompt": "Detailed description of what happens in this scene...",
      "end_image_prompt": "Detailed description of the final frame..."
    }}
  ]
}}
```"""

    async def plan_video(
        self, user_request: str, conversation_history: list[dict[str, str]] | None = None
    ) -> tuple[VideoRequirements | None, ScenePlan | None, str]:
        """Plan a video through conversational interaction.

        Args:
            user_request: Initial user request
            conversation_history: Previous conversation messages

        Returns:
            Tuple of (requirements, scene_plan, agent_response)
            - requirements: Extracted requirements (if complete)
            - scene_plan: Generated scene plan (if complete)
            - agent_response: Agent's message to the user
        """
        try:
            logger.info("planning_video", user_request=user_request[:100])

            # Build message history
            messages = conversation_history or []

            # If this is the first message, add the user request
            if not messages:
                messages.append({"role": "user", "content": user_request})

            # Call Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=self.create_planning_prompt(user_request),
                messages=messages,
            )

            # Extract response text
            response_text = response.content[0].text if response.content else ""

            # Try to extract scene plan if present
            requirements, scene_plan = self._extract_scene_plan(response_text)

            logger.info(
                "planning_response",
                has_requirements=requirements is not None,
                has_scene_plan=scene_plan is not None,
            )

            return requirements, scene_plan, response_text

        except Exception as e:
            logger.error("planning_failed", error=str(e))
            raise

    def _extract_scene_plan(
        self, response_text: str
    ) -> tuple[VideoRequirements | None, ScenePlan | None]:
        """Extract scene plan from response if present.

        Args:
            response_text: The agent's response

        Returns:
            Tuple of (requirements, scene_plan) or (None, None)
        """
        try:
            # Look for JSON code block
            if "```json" in response_text:
                # Extract JSON from code block
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()

                # Parse JSON
                data = json.loads(json_str)

                # Extract requirements
                req_data = data.get("requirements", {})
                requirements = VideoRequirements(
                    business_name=req_data.get("business_name"),
                    video_purpose=req_data.get("video_purpose", "video"),
                    duration=float(req_data.get("duration", 0)),
                    theme=req_data.get("theme"),
                )

                # Extract scenes
                scenes_data = data.get("scenes", [])
                scenes = []

                for scene_data in scenes_data:
                    scene = Scene(
                        scene_id=scene_data.get("scene_id", f"scene_{len(scenes) + 1}"),
                        duration=float(scene_data.get("duration", 5)),
                        video_prompt=scene_data["video_prompt"],
                        end_image_prompt=scene_data["end_image_prompt"],
                    )
                    scenes.append(scene)

                # Create scene plan
                scene_plan = ScenePlan(
                    total_duration=requirements.duration,
                    theme=requirements.theme,
                    scenes=scenes,
                )

                return requirements, scene_plan

        except Exception as e:
            logger.debug("no_scene_plan_extracted", error=str(e))

        return None, None

    def create_initial_state(
        self,
        requirements: VideoRequirements,
        scene_plan: ScenePlan,
    ) -> WorkflowState:
        """Create initial workflow state from requirements and plan.

        Args:
            requirements: Video requirements
            scene_plan: Scene plan

        Returns:
            Initial workflow state
        """
        session_id = str(uuid.uuid4())

        state = WorkflowState(
            session_id=session_id,
            status=WorkflowStatus.APPROVAL,
            requirements=requirements,
            scene_plan=scene_plan,
        )

        logger.info("initial_state_created", session_id=session_id)
        return state

    def calculate_optimal_scenes(self, duration: float, max_scene_duration: int = 8) -> int:
        """Calculate optimal number of scenes for a given duration.

        Args:
            duration: Total video duration in seconds
            max_scene_duration: Maximum duration per scene

        Returns:
            Number of scenes needed
        """
        return math.ceil(duration / max_scene_duration)

    def validate_scene_plan(self, scene_plan: ScenePlan) -> tuple[bool, str | None]:
        """Validate a scene plan.

        Args:
            scene_plan: The scene plan to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        config = get_config()
        max_duration = config.max_scene_duration

        # Check each scene
        for scene in scene_plan.scenes:
            if scene.duration > max_duration:
                return (
                    False,
                    f"Scene {scene.scene_id} duration {scene.duration}s exceeds maximum {max_duration}s",
                )

            if not scene.video_prompt:
                return False, f"Scene {scene.scene_id} missing video prompt"

            if not scene.end_image_prompt:
                return False, f"Scene {scene.scene_id} missing end image prompt"

        # Check total duration matches
        calculated_duration = sum(scene.duration for scene in scene_plan.scenes)
        if abs(calculated_duration - scene_plan.total_duration) > 0.5:
            return (
                False,
                f"Scene durations ({calculated_duration}s) don't match total ({scene_plan.total_duration}s)",
            )

        return True, None
