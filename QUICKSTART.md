# Claudio Quick Start Guide

Get started with Claudio in 5 minutes!

## Prerequisites

- Python 3.11 or higher
- FFmpeg
- API Keys:
  - Anthropic API key
  - Google AI API key

## Installation

### 1. Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH

### 2. Install Claudio

```bash
# Clone the repository
git clone <repository-url>
cd claudio

# Install dependencies
poetry install
# OR
pip install -e .
```

### 3. Configure API Keys

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

Add your keys:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
```

## Usage

### Interactive Mode

```bash
python .claude/skills/video-director/example.py
```

Example session:
```
What video would you like to create? Create a 15-second ad for Joe's Pizza with a 20% discount

Agent: Great! I'd love to help you create a promotional video. What style
       would you like? (e.g., fun and energetic, professional, etc.)

You: Fun and energetic

Agent: Perfect! And what video quality?
       - 720p (HD)
       - 1080p (Full HD)

You: 1080p

Agent: Here's the scene plan...
[Shows detailed scene breakdown]

Approve this plan? (yes/edit/no): yes

Estimated Cost:
Images: $0.30
Videos: $6.00
Total: $6.30

Proceed with generation? (yes/no): yes

📹 Generating scene end-frame images...
📹 Generating video segments...
📹 Combining video segments...

✅ Video Generation Complete!
Final Video: ~/.claudio/sessions/abc-123/final_video.mp4
```

### Automated Mode

For scripted workflows:

```bash
python .claude/skills/video-director/example.py auto
```

Or programmatically:

```python
import asyncio
from claudio.agents.scene_planner import ScenePlanningAgent
from claudio.agents.production_orchestrator import ProductionOrchestratorAgent

async def main():
    # Create a simple video request
    user_request = "Create a 10-second ad for my coffee shop"

    # Initialize planner
    planner = ScenePlanningAgent()

    # Get scene plan through conversation
    requirements, scene_plan, response = await planner.plan_video(user_request)

    # Once approved, create state and generate
    state = planner.create_initial_state(requirements, scene_plan)

    # Execute production
    orchestrator = ProductionOrchestratorAgent()
    await orchestrator.execute_full_production(state)

    print(f"Video ready: {state.assets.final_video}")

asyncio.run(main())
```

## Integration with Claude Code

Once installed, the video director skill is automatically available in Claude Code:

```
User: Create an advertisement for 20% off at my pizza shop

Claude: I'll help you create that video! Let me gather some details...
[Interactive conversation follows]
```

The skill activates on keywords like:
- "create video"
- "make advertisement"
- "generate commercial"
- "video promo"

## Typical Workflow

1. **Request** - User describes the video they want
2. **Plan** - Agent asks questions and creates scene breakdown
3. **Review** - User reviews and approves/edits the plan
4. **Estimate** - System shows cost estimate
5. **Generate** - Parallel image and video generation
6. **Deliver** - Final video ready in workspace

## Cost Management

### Default Pricing
- Images: $0.10 per image
- Videos: $0.40 per second

### Example Costs
- 10-second video (2 scenes): ~$4.20
- 20-second video (4 scenes): ~$8.40
- 30-second video (6 scenes): ~$12.60

Costs are always shown before generation starts.

## Output Location

All generated assets are saved to:
```
~/.claudio/sessions/{session_id}/
├── state.json              # Workflow state
├── images/                 # Scene end-frame images
├── videos/                 # Individual scene videos
└── final_video.mp4        # Your final video!
```

## Troubleshooting

### "API key not found"
Make sure you've created `.env` and added your keys.

### "FFmpeg not found"
Install FFmpeg and ensure it's in your PATH. Test with: `ffmpeg -version`

### "Duration exceeds maximum"
Individual scenes are limited to 8 seconds. The planner automatically breaks longer videos into multiple scenes.

### "Cost estimation failed"
Check that your API keys are valid and have sufficient quota.

### Videos won't concatenate
Ensure all scenes generated successfully. Check logs for individual scene failures.

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore the [SKILL.md](.claude/skills/video-director/SKILL.md) for skill details
- Check out API client code for customization options
- Modify cost estimates in `.env` if needed

## Support

For issues or questions:
- Check the logs in your console
- Review the workflow state in `~/.claudio/sessions/{id}/state.json`
- Ensure all dependencies are installed correctly

Happy video creating! 🎬
