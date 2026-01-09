"""Example usage of the Claudio video generation system."""

import asyncio

from claudio.agents.production_orchestrator import ProductionOrchestratorAgent
from claudio.agents.scene_planner import ScenePlanningAgent
from claudio.config import get_config


async def create_video_interactive(user_request: str) -> None:
    """Create a video through interactive conversation.

    Args:
        user_request: Initial user request for video creation
    """
    print(f"\\n{'='*60}")
    print("Claudio Video Director")
    print(f"{'='*60}\\n")

    # Initialize config
    config = get_config()
    config.validate_api_keys()
    config.ensure_workspace_dirs()

    # Phase 1: Scene Planning
    print("Phase 1: Scene Planning\\n")
    planner = ScenePlanningAgent()
    conversation = []

    # Interactive conversation loop
    while True:
        requirements, scene_plan, response = await planner.plan_video(
            user_request, conversation
        )

        # Show agent response
        print(f"Agent: {response}\\n")

        # Check if we have a complete plan
        if requirements and scene_plan:
            # Validate the plan
            valid, error = planner.validate_scene_plan(scene_plan)
            if not valid:
                print(f"⚠️  Plan validation failed: {error}\\n")
                user_input = input("Your response: ")
                conversation.append({"role": "assistant", "content": response})
                conversation.append({"role": "user", "content": user_input})
                continue

            # Ask for approval
            approval = input("\\nApprove this plan? (yes/edit/no): ")

            if approval.lower() == "yes":
                # Create initial state
                state = planner.create_initial_state(requirements, scene_plan)
                break
            elif approval.lower() == "edit":
                # Get edit request
                edit_request = input("What would you like to change? ")
                conversation.append({"role": "assistant", "content": response})
                conversation.append({"role": "user", "content": edit_request})
                continue
            else:
                print("\\n❌ Plan rejected. Exiting...\\n")
                return
        else:
            # Continue conversation
            user_input = input("You: ")
            conversation.append({"role": "assistant", "content": response})
            conversation.append({"role": "user", "content": user_input})

    # Phase 2: Cost Estimation
    print(f"\\n{'='*60}")
    print("Phase 2: Cost Estimation\\n")

    orchestrator = ProductionOrchestratorAgent()
    cost_result = await orchestrator.estimate_cost(state)

    if cost_result["success"]:
        print("Estimated Cost:")
        print(cost_result["formatted"])
        print()

        proceed = input("Proceed with generation? (yes/no): ")
        if proceed.lower() != "yes":
            print("\\n❌ Generation cancelled.\\n")
            return
    else:
        print(f"⚠️  Cost estimation failed: {cost_result.get('error')}\\n")

    # Phase 3: Production
    print(f"\\n{'='*60}")
    print("Phase 3: Video Production\\n")

    async def progress_callback(message: str) -> None:
        """Print progress updates."""
        print(f"📹 {message}")

    try:
        state = await orchestrator.execute_full_production(
            state, progress_callback=progress_callback
        )

        print(f"\\n{'='*60}")
        print("✅ Video Generation Complete!")
        print(f"{'='*60}\\n")
        print(f"Session ID: {state.session_id}")
        print(f"Final Video: {state.assets.final_video}")

        # Show scene details
        if state.scene_plan:
            print(f"\\nScenes Generated: {len(state.scene_plan.scenes)}")
            print(f"Total Duration: {state.scene_plan.total_duration}s")
            print(f"Quality: {state.scene_plan.quality}")

        print(f"\\n{'='*60}\\n")

    except Exception as e:
        print(f"\\n{'='*60}")
        print("❌ Production Failed")
        print(f"{'='*60}\\n")
        print(f"Error: {e}\\n")
        raise


async def create_video_automated(
    business_name: str,
    video_purpose: str,
    duration: float,
    theme: str,
    quality: str = "1080p",
) -> None:
    """Create a video with predefined parameters (non-interactive).

    Args:
        business_name: Name of the business/product
        video_purpose: Purpose of the video
        duration: Video duration in seconds
        theme: Theme/style of the video
        quality: Video quality (720p or 1080p)
    """
    print(f"\\n{'='*60}")
    print("Claudio Video Director (Automated Mode)")
    print(f"{'='*60}\\n")

    # Initialize config
    config = get_config()
    config.validate_api_keys()
    config.ensure_workspace_dirs()

    from claudio.models.scene import Scene, ScenePlan, VideoRequirements

    # Create requirements
    requirements = VideoRequirements(
        business_name=business_name,
        video_purpose=video_purpose,
        duration=duration,
        theme=theme,
        quality=quality,
    )

    # Calculate scene count
    planner = ScenePlanningAgent()
    scene_count = planner.calculate_optimal_scenes(duration)

    # Create simple scene plan (this is simplified - in practice, use the agent)
    scenes = []
    scene_duration = duration / scene_count

    for i in range(scene_count):
        scene = Scene(
            scene_id=f"scene_{i+1}",
            duration=scene_duration,
            video_prompt=f"Scene {i+1} showing {business_name}",
            end_image_prompt=f"End frame for scene {i+1} of {business_name}",
        )
        scenes.append(scene)

    scene_plan = ScenePlan(
        total_duration=duration, quality=quality, theme=theme, scenes=scenes
    )

    # Create state
    state = planner.create_initial_state(requirements, scene_plan)

    # Cost estimation
    orchestrator = ProductionOrchestratorAgent()
    cost_result = await orchestrator.estimate_cost(state)

    if cost_result["success"]:
        print("Estimated Cost:")
        print(cost_result["formatted"])
        print()

    # Execute production
    print("Starting video production...\\n")

    try:
        state = await orchestrator.execute_full_production(state)

        print(f"\\n✅ Video generated successfully!")
        print(f"Final Video: {state.assets.final_video}\\n")

    except Exception as e:
        print(f"\\n❌ Production failed: {e}\\n")
        raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "auto":
        # Automated mode example
        asyncio.run(
            create_video_automated(
                business_name="Joe's Pizza",
                video_purpose="20% discount advertisement",
                duration=15.0,
                theme="fun, energetic, family-friendly",
                quality="1080p",
            )
        )
    else:
        # Interactive mode
        user_request = input("What video would you like to create? ")
        asyncio.run(create_video_interactive(user_request))