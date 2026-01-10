"""Example usage of the Claudio video generation system."""

import asyncio

from agents.production_orchestrator import ProductionOrchestratorAgent
from agents.scene_planner import ScenePlanningAgent
from config import get_config

async def generate_video(state) -> None:
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

        print(f"\\n{'='*60}\\n")

    except Exception as e:
        print(f"\\n{'='*60}")
        print("❌ Production Failed")
        print(f"{'='*60}\\n")
        print(f"Error: {e}\\n")
        raise


async def create_video_interactive() -> None:
    """Create a video through interactive conversation.
    """
    user_request = input("What video would you like to create? ")

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
                return await generate_video(state)
            elif approval.lower() == "edit":
                # Get edit request
                edit_request = input("What would you like to change? ")
                conversation.append({"role": "assistant", "content": response})
                conversation.append({"role": "user", "content": edit_request})
                continue
            else:
                print("\\n❌ Plan rejected. Exiting...\\n")
                return None
        else:
            # Continue conversation
            user_input = input("You: ")
            conversation.append({"role": "assistant", "content": response})
            conversation.append({"role": "user", "content": user_input})


if __name__ == "__main__":
    asyncio.run(create_video_interactive())
