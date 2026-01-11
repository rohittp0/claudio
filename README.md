# Claudio - AI Video Director

Claudio is an AI-powered video generation system that creates professional videos using Google's Veo 3.1 and Imagen (Nano Banana) APIs. It combines intelligent scene planning with parallel video production to generate multi-scene videos with smooth transitions.

## Features

- **Conversational Scene Planning**: Interactive planning agent that gathers requirements through natural conversation
- **Automatic Scene Breakdown**: Intelligently splits longer videos into 8-second segments (Veo 3.1 constraint)
- **Parallel Production**: Generates images and videos in parallel for optimal performance
- **Image-to-Video Continuity**: Uses end-frame images as start-frame for next scene to ensure smooth transitions
- **Cost Estimation**: Calculates costs before generation
- **Stateful Workflow**: Saves and resumes sessions

## Prerequisites

- Python 3.13+ (tested with 3.13)
- [Anthropic API Key](https://console.anthropic.com/) (for Claude)
- [Google AI API Key](https://aistudio.google.com/app/apikey) (for Veo 3.1 and Imagen)
- FFmpeg (for video concatenation)

### Install FFmpeg

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

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd claudio
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

### 3. Activate Virtual Environment

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# Required API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_API_KEY=your_google_api_key_here

# Optional: Workspace Configuration
WORKSPACE_DIR=~/.claudio
LOG_LEVEL=INFO

# Optional: Cost Estimation (USD)
NANO_BANANA_COST_PER_IMAGE=0.10
VEO_COST_PER_SECOND=0.40

# Optional: Video Generation Defaults
MAX_SCENE_DURATION=8
```

### 6. Create Workspace Directory

The workspace directory stores session data, generated images, and videos:

```bash
mkdir -p ~/.claudio
```

## Usage

### Interactive Mode

Run the main script to start an interactive video generation session:

```bash
python main.py
```

You'll be guided through three phases:

#### Phase 1: Scene Planning
The AI agent will ask you questions to understand your video requirements:
- What type of video you want
- Business/product name
- Desired duration
- Theme and style
- Additional context

The agent will then create a detailed scene plan breaking your video into 8-second segments.

#### Phase 2: Cost Estimation
Review the estimated cost for generating images and videos before proceeding.

#### Phase 3: Production
Claudio will:
1. Generate end-frame images for all scenes (in parallel)
2. Generate video segments using Veo 3.1 (in parallel)
3. Concatenate all segments into a final video

### Example Session

```bash
$ python main.py
What video would you like to create? A 20-second advertisement for Joe's Pizza showing their new special

============================================================
Claudio Video Director
============================================================

Phase 1: Scene Planning

Agent: I'd be happy to help you create a 20-second advertisement for Joe's Pizza! Let me gather some details.

What's the theme or style you're looking for? (e.g., fun and energetic, professional, family-friendly)

You: Fun and family-friendly

Agent: Great! For a 20-second video, I'll create 3 scenes of 8 seconds, 8 seconds, and 4 seconds...

[Scene plan presented]

Approve this plan? (yes/edit/no): yes

============================================================
Phase 2: Cost Estimation

Estimated Cost:
Images: $0.30
Videos: $8.00
Total: $8.30

Proceed with generation? (yes/no): yes

============================================================
Phase 3: Video Production

📹 Generating scene_1 image...
📹 Generating scene_2 image...
📹 Generating scene_3 image...
📹 All images generated (3/3)
📹 Generating scene_1 video...
📹 Generating scene_2 video...
📹 Generating scene_3 video...
📹 All videos generated (3/3)
📹 Concatenating final video...

============================================================
✅ Video Generation Complete!
============================================================

Session ID: 550e8400-e29b-41d4-a716-446655440000
Final Video: /Users/you/.claudio/sessions/550e8400-e29b-41d4-a716-446655440000/final.mp4

Scenes Generated: 3
Total Duration: 20.0s

============================================================
```

### Using with Claude Code CLI

Claudio can also be used as an MCP (Model Context Protocol) skill in Claude Code CLI, allowing Claude to act as your video director agent.

#### Setup

The skill is automatically discovered by Claude Code CLI from the `.claude/skills/video-director/` directory. Simply ensure you have:

1. Installed dependencies: `pip install -r requirements.txt`
2. Configured API keys in `.env` file
3. FFmpeg installed on your system

#### Usage

Ask Claude to create a video naturally:

```
Create a 20-second advertisement for Joe's Pizza
```

Claude will:
1. **Ask clarifying questions** to understand your requirements
2. **Plan scenes** automatically (breaking into 8-second segments)
3. **Estimate costs** and ask for approval
4. **Generate images** for each scene's end-frame
5. **Generate videos** using Veo 3.1 with image constraints
6. **Concatenate** all segments into a final video
7. **Return the path** to your completed video

#### Available MCP Tools

When using Claude Code CLI, Claude has access to these tools:

- **create_session_id()** - Generate unique session identifier
- **estimate_cost()** - Calculate generation costs before proceeding
- **generate_image()** - Create end-frame images using Imagen
- **generate_video()** - Generate 8-second video segments using Veo 3.1
- **concatenate_videos()** - Combine segments into final video
- **save_workflow_state()** - Persist workflow for resuming later
- **load_workflow_state()** - Resume a previous workflow

#### Example Conversation

```
You: Create a 15-second coffee commercial with a modern aesthetic

Claude: I'll create a 15-second coffee commercial for you! To make it perfect, I need a bit more info:
        1. What's the main message? (e.g., "Best coffee in town", "New seasonal blend")
        2. Any specific scenes you want? (e.g., coffee being poured, people enjoying it)

You: Focus on the brewing process and the rich aroma. Message: "Handcrafted Excellence"

Claude: Perfect! For 15 seconds, I'll plan 2 scenes:

        Scene 1 (8s): Close-up of coffee being ground, steam rising, beans falling
        Scene 2 (7s): Pour-over brewing process, final cup with "Handcrafted Excellence" overlay

        Let me estimate the cost...
        [Uses estimate_cost tool]

        Total: $6.20 ($0.20 for images + $6.00 for videos)

        Shall I proceed?

You: Yes

Claude: [Creates session ID]
        [Generates scene_1 end-frame image]
        [Generates scene_2 end-frame image]
        [Generates scene_1 video]
        [Generates scene_2 video with scene_1's end-frame as start]
        [Concatenates videos]

        ✓ Done! Your video is ready at: ~/.claudio/sessions/abc-123/final.mp4
```

#### Advantages vs Python CLI

- **Natural conversation** - Claude understands context and asks relevant questions
- **No separate planning agent** - Claude IS the planning agent
- **Flexible workflow** - Adapt on the fly based on user feedback
- **Full context** - Works with Claude Code's understanding of your project
- **Reusable tools** - Same tools can be used by any MCP client

#### Testing the MCP Server

To test the server manually:

```bash
# Start the server (waits for JSON-RPC messages on stdin)
python mcp_server.py

# In another terminal, use MCP Inspector to test
npm install -g @modelcontextprotocol/inspector
mcp-inspector python mcp_server.py
```

## Project Structure

```
claudio/
├── agents/                     # AI agents
│   ├── scene_planner.py       # Conversational scene planning agent
│   └── production_orchestrator.py  # Parallel production execution
├── api_clients/               # API client wrappers
│   ├── base_client.py        # Base client with retry logic
│   ├── nano_banana_client.py # Imagen image generation
│   └── veo_client.py         # Veo 3.1 video generation
├── models/                    # Data models
│   ├── scene.py              # Scene and plan models
│   └── workflow_state.py     # Workflow state management
├── tools/                     # MCP tool handlers
│   └── tools.py              # Video generation tools
├── utils/                     # Utilities
│   ├── async_utils.py        # Async helpers
│   ├── file_manager.py       # File path management
│   └── state_manager.py      # State persistence
├── config.py                  # Configuration management
├── main.py                    # Main entry point
└── requirements.txt           # Python dependencies
```

## API Information

### Veo 3.1 (Video Generation)

- **Model**: `veo-3.1-generate-preview`
- **Fixed Duration**: 8 seconds per video
- **Resolution**: Automatic (fixed)
- **Cost**: ~$0.40 per second
- **API**: Google GenAI SDK

### Imagen / Nano Banana (Image Generation)

- **Model**: `gemini-2.5-flash-image`
- **Aspect Ratio**: 16:9 (configurable)
- **Quality**: HD or Standard
- **Cost**: ~$0.10 per image
- **API**: Google GenAI SDK

## Configuration

All configuration is managed through environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | **Required** |
| `GOOGLE_API_KEY` | Google AI API key for Veo/Imagen | **Required** |
| `WORKSPACE_DIR` | Directory for session data | `~/.claudio` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `NANO_BANANA_COST_PER_IMAGE` | Cost per image (USD) | `0.10` |
| `VEO_COST_PER_SECOND` | Cost per video second (USD) | `0.40` |
| `MAX_SCENE_DURATION` | Maximum scene duration (seconds) | `8` |

## How It Works

### 1. Scene Planning
The Scene Planning Agent uses Claude to:
- Gather requirements through conversation
- Break videos into 8-second scenes (Veo constraint)
- Generate detailed video prompts for each scene
- Create end-frame image descriptions

### 2. Image Generation
For each scene, Claudio generates an end-frame image that represents the final frame of that scene's video. This image is used by Veo to ensure the video ends exactly at this frame.

### 3. Video Generation
Veo 3.1 generates each video segment using:
- **Video prompt**: Describes what happens in the scene
- **End-frame image**: Ensures video ends at this exact frame
- **Start-frame image** (optional): Previous scene's end-frame for continuity

### 4. Concatenation
All video segments are concatenated using FFmpeg to create the final video.

## Workflow States

Claudio tracks workflow through these states:
- `PLANNING`: Gathering requirements
- `APPROVAL`: Waiting for user approval
- `GENERATING_IMAGES`: Creating end-frame images
- `GENERATING_VIDEOS`: Creating video segments
- `CONCATENATING`: Combining segments
- `COMPLETED`: Final video ready
- `FAILED`: Error occurred

## Cost Considerations

Example costs for a 25-second video (4 scenes):
- Images: 4 scenes × $0.10 = $0.40
- Videos: 25 seconds × $0.40 = $10.00
- **Total**: ~$10.40

Actual costs may vary based on Google AI pricing.

## Limitations

- **Veo 3.1**: Fixed 8-second duration per segment (API limitation)
- **Video Quality**: Not configurable (automatic in Veo 3.1)
- **Aspect Ratio**: 16:9 for images (configurable), videos follow Veo defaults
- **Generation Time**: ~30-60 seconds per video segment
- **API Rate Limits**: Subject to Google AI rate limits

## Troubleshooting

### FFmpeg Not Found
```bash
# Install FFmpeg first
brew install ffmpeg  # macOS
sudo apt-get install ffmpeg  # Ubuntu
```

### API Key Errors
```bash
# Verify your .env file has correct API keys
cat .env | grep API_KEY
```

### Permission Errors
```bash
# Ensure workspace directory is writable
chmod -R 755 ~/.claudio
```

### Module Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
# Install dev dependencies
pip install black isort ruff

# Format code
black .
isort .
ruff check .
```

## License

[Add your license here]

## Contributing

[Add contributing guidelines here]

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions

## Acknowledgments

- Built with [Claude](https://www.anthropic.com/claude) by Anthropic
- Uses Google's [Veo 3.1](https://deepmind.google/technologies/veo/) for video generation
- Uses Google's [Imagen](https://deepmind.google/technologies/imagen-3/) for image generation
