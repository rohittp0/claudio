---
name: video-director
description: Create professional videos from text descriptions using AI-powered scene planning and video generation
activation:
  - video
  - advertisement
  - commercial
  - promo
---

# Video Director Skill

## Purpose

This skill helps users create professional videos through an intelligent, interactive workflow. It uses Claude for conversational planning, Google Veo 3 for video generation, and Nano Banana for image generation to create seamless, high-quality videos from simple text descriptions.

## How It Works

### 1. Requirements Gathering
When activated, the skill invokes the Scene Planning Agent to:
- Ask follow-up questions about the video (business name, duration, theme, style, quality)
- Gather all necessary information through natural conversation
- Create a detailed scene-by-scene plan

### 2. Scene Plan Review
Once the agent creates a plan, it presents:
- Complete scene breakdown with descriptions
- Duration for each scene
- Video and image prompts
- Opportunity for user to request changes or approve

### 3. Cost Estimation
Before generation begins, the system shows:
- Image generation costs (Nano Banana API)
- Video generation costs (Veo 3 API)
- Total estimated cost
- Asks for confirmation to proceed

### 4. Video Production
Upon approval, the Production Orchestrator executes:
- **Image Generation**: Creates end-frame images for all scenes in parallel
- **Video Generation**: Generates all video segments in parallel with proper continuity
  - First scene uses only end image
  - Subsequent scenes use previous end image as start for smooth transitions
- **Concatenation**: Combines all segments into final video using ffmpeg

### 5. Delivery
The final video is saved to:
```
~/.claudio/sessions/{session_id}/final_video.mp4
```

## Activation Examples

This skill activates when users request video creation:

- "Create an advertisement for 20% off at my pizza shop"
- "Make a promotional video for my coffee shop"
- "Generate a video commercial for our new product"
- "I need a video ad for my business"

## Workflow

```python
import asyncio
from claudio.agents.scene_planner import ScenePlanningAgent
from claudio.agents.production_orchestrator import ProductionOrchestratorAgent
from claudio.utils.state_manager import StateManager

async def create_video(user_request: str):
    # Phase 1: Scene Planning
    planner = ScenePlanningAgent()
    conversation = []

    # Interactive conversation loop
    while True:
        requirements, scene_plan, response = await planner.plan_video(
            user_request,
            conversation
        )

        # Show response to user
        print(response)

        # Check if we have a complete plan
        if requirements and scene_plan:
            # Validate the plan
            valid, error = planner.validate_scene_plan(scene_plan)
            if not valid:
                print(f"Plan validation failed: {error}")
                continue

            # Ask for approval
            user_input = input("Approve this plan? (yes/edit/no): ")

            if user_input.lower() == "yes":
                # Create initial state
                state = planner.create_initial_state(requirements, scene_plan)
                break
            elif user_input.lower() == "edit":
                # Get edit request
                edit_request = input("What would you like to change? ")
                conversation.append({"role": "user", "content": edit_request})
                continue
            else:
                print("Plan rejected. Starting over...")
                return
        else:
            # Continue conversation
            user_input = input("Your response: ")
            conversation.append({"role": "assistant", "content": response})
            conversation.append({"role": "user", "content": user_input})

    # Phase 2: Cost Estimation
    orchestrator = ProductionOrchestratorAgent()
    cost_result = await orchestrator.estimate_cost(state)

    if cost_result["success"]:
        print(f"\\nEstimated Cost:\\n{cost_result['formatted']}")

        proceed = input("Proceed with generation? (yes/no): ")
        if proceed.lower() != "yes":
            print("Generation cancelled.")
            return

    # Phase 3: Production
    print("\\nStarting video production...")

    try:
        state = await orchestrator.execute_full_production(
            state,
            progress_callback=lambda msg: print(f"Status: {msg}")
        )

        print(f"\\n✅ Video generation complete!")
        print(f"Final video: {state.assets.final_video}")

    except Exception as e:
        print(f"\\n❌ Production failed: {e}")
        raise

# Example usage
if __name__ == "__main__":
    user_request = "Create an advertisement for 20% off at my pizza shop"
    asyncio.run(create_video(user_request))
```

## Technical Details

### Scene Constraints
- Maximum 8 seconds per scene (Veo API limit)
- Automatic scene breakdown for longer videos
- Each scene has detailed video and image prompts

### Video Continuity
The system ensures smooth transitions between scenes:
- Scene 1: Generated with end image only
- Scene 2+: Generated with previous scene's end image as start, current scene's end image as end
- This creates seamless visual flow between segments

### Parallel Processing
- All images generated concurrently
- All videos generated concurrently (after images complete)
- Significantly reduces total generation time

### Error Handling
- Automatic retry with exponential backoff for API failures
- Partial failure handling (continues with successful scenes)
- State persistence allows resuming from interruptions

### State Management
All workflow state is persisted to:
```
~/.claudio/sessions/{session_id}/
├── state.json              # Workflow state
├── images/                 # Generated images
│   ├── scene_1_end.png
│   └── scene_2_end.png
├── videos/                 # Generated video segments
│   ├── scene_1.mp4
│   └── scene_2.mp4
└── final_video.mp4        # Final concatenated video
```

## Cost Considerations

Typical costs for a 20-second video (5 scenes):
- Images: ~$0.50 (5 images × $0.10)
- Videos: ~$8.00 (20 seconds × $0.40)
- **Total: ~$8.50**

Costs are estimated before generation and user must confirm to proceed.

## Configuration

Set up API keys in `.env`:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key
GOOGLE_API_KEY=your_google_api_key
```

Adjust cost rates and defaults in `.env`:
```env
NANO_BANANA_COST_PER_IMAGE=0.10
VEO_COST_PER_SECOND=0.40
DEFAULT_VIDEO_QUALITY=1080p
MAX_SCENE_DURATION=8
```

## Troubleshooting

### "No scene plan extracted"
The agent is still gathering requirements. Continue the conversation by answering its questions.

### "Duration exceeds maximum"
Individual scenes cannot exceed 8 seconds. The planner will automatically break longer durations into multiple scenes.

### "Image generation failed"
Check your Google API key and quota. The system will retry failed scenes automatically.

### "FFmpeg not found"
Install FFmpeg:
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt-get install ffmpeg`
- Windows: Download from ffmpeg.org

## Example Session

```
User: Create a 15-second ad for 20% off at Joe's Pizza

Agent: Great! I'd love to help you create a promotional video for Joe's Pizza.
       Let me gather a few details:

       What style would you like for this advertisement? (e.g., fun and energetic,
       professional, family-friendly, etc.)

User: Fun and energetic

Agent: Perfect! And what video quality would you prefer?
       - 720p (HD) - faster, lower cost
       - 1080p (Full HD) - higher quality, recommended

User: 1080p

Agent: Excellent! Here's the scene plan I've created for your 15-second video:

[Scene Plan JSON displayed]

Scene 1 (5s): Camera zooms into Joe's Pizza storefront with neon sign glowing...
Scene 2 (5s): Inside kitchen, fresh pizza being prepared with toppings...
Scene 3 (5s): Close-up of finished pizza, text overlay "20% OFF THIS WEEK"

Does this look good?

User: Yes, approve

Agent: Great! Let me estimate the cost:

Estimated Cost:
Images: $0.30
Videos: $6.00
Total: $6.30

Proceed with generation? (yes/no)

User: yes

Agent: Starting video production...
Status: Generating scene end-frame images...
Status: Generating video segments...
Status: Combining video segments...

✅ Video generation complete!
Final video: ~/.claudio/sessions/abc-123/final_video.mp4
```

## Notes

- This skill requires active API keys for Anthropic and Google
- Video generation can take several minutes depending on scene count
- All assets are saved locally for review and reuse
- The system maintains full state, allowing resumption after interruptions