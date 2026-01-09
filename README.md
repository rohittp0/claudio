# Claudio - AI-Powered Video Generation System

Claudio is an intelligent video generation system that integrates with Claude Code CLI. It uses Claude Agent SDK for conversational planning, Google Veo 3 for video generation, and Nano Banana for image generation to create professional videos from simple text prompts.

## Features

- **Conversational Video Planning**: Interactive requirements gathering through Claude Agent SDK
- **Intelligent Scene Breakdown**: Automatic scene planning with optimal duration and continuity
- **Cost Estimation**: Transparent cost preview before generation
- **Parallel Processing**: Efficient parallel image and video generation
- **Seamless Continuity**: Smart image-to-video transitions between scenes
- **Error Recovery**: Robust retry logic and state persistence
- **Claude Code Integration**: Works as a skill in Claude Code CLI

## Architecture

```
User Request → Claude Code Skill → Video Director Agent (SDK) → MCP Tools → APIs
                     ↓                       ↓                      ↓
              Orchestrates           Scene Planning          Veo 3, Nano Banana
              Workflow              + Production            + FFmpeg operations
```

## Prerequisites

- Python 3.11 or higher
- FFmpeg installed on your system
- API Keys:
  - Anthropic API key (for Claude)
  - Google AI API key (for Veo 3 and Nano Banana)

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd claudio
```

### 2. Install dependencies

Using Poetry (recommended):
```bash
poetry install
```

Or using pip:
```bash
pip install -e .
```

### 3. Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key
GOOGLE_API_KEY=your_google_api_key
```

## Usage

### As a Claude Code Skill

1. Ensure Claude Code CLI is installed
2. Start a conversation in Claude Code
3. Request a video:

```
User: Create an advertisement for 20% off at my pizza shop
```

The system will:
1. Ask follow-up questions (shop name, duration, theme, quality)
2. Generate a scene-by-scene plan
3. Show estimated costs
4. Request approval
5. Generate images and videos in parallel
6. Deliver the final video

### Scene Plan Approval

After the system creates a scene plan, you can:
- **Approve**: Proceed with generation
- **Request changes**: "Make scene 2 more energetic"
- **Edit specific scenes**: "Change the ending"

The system will conversationally refine the plan until you're satisfied.

## Project Structure

```
claudio/
├── agents/                     # Claude Agent SDK agents
│   ├── scene_planner.py       # Requirements gathering & scene planning
│   └── production_orchestrator.py  # Production execution
├── mcp_server/                # In-process MCP server
│   ├── tools.py               # Tool definitions
│   └── server.py              # MCP server setup
├── api_clients/               # External API clients
│   ├── veo_client.py          # Veo 3 API integration
│   └── nano_banana_client.py  # Nano Banana API integration
├── models/                    # Data models
│   ├── scene.py               # Scene data structures
│   └── workflow_state.py      # State management
├── services/                  # Business logic
│   ├── scene_planning_service.py
│   ├── image_generation_service.py
│   ├── video_generation_service.py
│   └── video_concatenation_service.py
└── utils/                     # Utilities
    ├── state_manager.py       # State persistence
    ├── file_manager.py        # Asset management
    └── async_utils.py         # Async helpers

.claude/skills/video-director/  # Claude Code Skill integration
tests/                          # Test suite
```

## How It Works

### 1. Requirements Gathering
The Scene Planning Agent asks questions to understand your video needs:
- Business/product name
- Video purpose
- Duration (flexible)
- Theme and style
- Video quality (720p/1080p)

### 2. Scene Planning
The agent creates a detailed scene plan:
- Breaks video into optimal scenes (max 8 seconds each for Veo API)
- Generates video prompts for each scene
- Creates end-image descriptions for continuity
- Returns structured scene list

### 3. Cost Estimation
Before generation, the system calculates and shows:
- Image generation costs (Nano Banana)
- Video generation costs (Veo 3)
- Total estimated cost

### 4. Production
Upon approval, the Production Orchestrator:
1. **Generates images** (parallel) for all scene end-frames
2. **Generates videos** (parallel):
   - Scene 1: Uses only end image
   - Scene 2+: Uses previous end image as start, current end image as end
3. **Concatenates** videos into final product using FFmpeg

### 5. Delivery
Final video is saved to:
```
~/.claudio/sessions/{session_id}/final_video.mp4
```

## State Management

Claudio persists workflow state, allowing resumption after interruptions:

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

## Technical Details

### Veo 3 API Constraints
- Maximum 8 seconds per video segment
- Supports image-to-video mode with start and end frames
- Generated videos maintain temporal coherence

### Nano Banana API
- Generates high-quality images for scene transitions
- All images include SynthID watermark
- Narrative prompts recommended over keywords

### Parallel Processing
- Images: All scenes generated concurrently
- Videos: All scenes generated concurrently (after images complete)
- Concatenation: Sequential (order matters)

### Error Handling
- API client level: Exponential backoff retry
- Service level: Partial failure handling
- Agent level: Verification loops
- State persistence: Resume from failures

## Development

### Running Tests

```bash
poetry run pytest
```

### Code Formatting

```bash
poetry run black claudio/
poetry run ruff claudio/
```

### Type Checking

```bash
poetry run mypy claudio/
```

## Cost Considerations

Typical costs for a 20-second video (5 scenes):
- Images: ~$0.50 (5 images × $0.10)
- Videos: ~$8.00 (20 seconds × $0.40)
- **Total: ~$8.50**

Costs are estimated before generation and can be customized in `.env`.

## Troubleshooting

### FFmpeg Not Found
Ensure FFmpeg is installed and in your PATH:
```bash
ffmpeg -version
```

### API Rate Limits
The system includes automatic retry logic with exponential backoff. If you hit rate limits frequently, consider:
- Reducing scene count
- Shorter video durations
- Spacing out requests

### Out of Memory
For long videos with many scenes:
- Use 720p instead of 1080p
- Generate fewer scenes
- Ensure sufficient disk space in workspace directory

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

[Add your license here]

## Acknowledgments

- Built with [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview)
- Powered by [Google Veo 3](https://ai.google.dev/gemini-api/docs/video) and [Nano Banana](https://ai.google.dev/gemini-api/docs/image-generation)
- Integrated with [Claude Code CLI](https://claude.com/claude-code)
