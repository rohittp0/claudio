# Video Director Skill

AI-powered video generation using Google Veo 3.1 and Imagen (Nano Banana).

## What It Does

This skill enables Claude to act as your video director, creating professional videos from text descriptions. Claude can:

- **Plan multi-scene videos** by breaking down your requirements
- **Estimate costs** before generation
- **Generate end-frame images** for each scene using Imagen
- **Create 8-second video segments** using Veo 3.1
- **Concatenate segments** into a final video
- **Save and resume** workflows for long-running projects

## How It Works

### Image Generation

Claudio uses Google's Imagen (via Nano Banana) to generate key frames:
- **First scene**: Generates BOTH a start-frame and end-frame image
  - Start-frame: Initial state before action begins
  - End-frame: Final state after the scene action
- **Subsequent scenes**: Only generates end-frame images
  - Start-frame: Uses previous scene's end-frame for smooth transitions

### Video Generation

Veo 3.1 uses interpolation mode which REQUIRES both start and end frames:
- Takes two images (start and end) and generates an 8-second video interpolating between them
- Creates smooth motion from start frame to end frame
- Each video segment is exactly 8 seconds (API constraint)

### Workflow

1. **Planning**: Claude asks questions to understand your video requirements (duration, theme, purpose)
2. **Scene Breakdown**: For videos longer than 8 seconds, Claude creates multiple scenes
3. **Cost Estimation**: Claude calculates the cost before proceeding
4. **Image Generation**:
   - First scene: Generates start-frame AND end-frame images
   - Other scenes: Generates only end-frame images
5. **Video Generation**: Creates 8-second video segments using interpolation between start and end frames
6. **Concatenation**: Combines all segments into the final video

### Example Interaction

```
You: Create a 20-second advertisement for Joe's Pizza

Claude: I'll help you create a 20-second advertisement! To plan this effectively, I need some details:

1. What's the main message or special you want to highlight?
2. What theme would you like - fun and energetic, professional, or family-friendly?

You: Fun and family-friendly. We're running a 20% discount on large pizzas.

Claude: Perfect! For a 20-second video, I'll create 3 scenes (8s + 8s + 4s):

Scene 1 (8s): Camera zooms into vibrant Joe's Pizza storefront with neon sign glowing at dusk
Scene 2 (8s): Close-up of hands preparing fresh pizza with toppings, steam rising
Scene 3 (4s): Happy family enjoying pizza together, text overlay: "20% OFF Large Pizzas!"

Let me estimate the cost first...
[Calls estimate_cost tool]

Total estimated cost: $8.30
- Images: $0.30 (3 images @ $0.10 each)
- Videos: $8.00 (20 seconds @ $0.40/second)

Should I proceed with generation?

You: Yes

Claude: Great! Generating images for all scenes...
[Generates scene_1, scene_2, scene_3 end-frame images]

Now generating video segments...
[Generates video_1, video_2, video_3]

Combining into final video...
[Concatenates all segments]

✓ Video generated successfully!
Final video: ~/.claudio/sessions/abc-123/final.mp4
```

## Available Tools

### 1. create_session_id()
Generates a unique session ID for tracking assets.

### 2. generate_image(session_id, scene_id, prompt, aspect_ratio="16:9", quality="hd")
Creates end-frame images using Imagen.

**Parameters:**
- `session_id`: Unique identifier for this workflow
- `scene_id`: Scene identifier (e.g., "scene_1")
- `prompt`: Detailed image description
- `aspect_ratio`: Image aspect ratio (default: "16:9")
- `quality`: "hd" or "standard" (default: "hd")

### 3. generate_video(session_id, scene_id, prompt, end_image_path, start_image_path)
Generates 8-second video segments using Veo 3.1's interpolation mode.

**Parameters:**
- `session_id`: Session identifier
- `scene_id`: Scene identifier
- `prompt`: What happens in this 8-second scene
- `end_image_path`: Path to end-frame image (required)
- `start_image_path`: Path to start-frame image (required for interpolation)

### 4. concatenate_videos(session_id, video_paths)
Combines video segments using FFmpeg.

**Parameters:**
- `session_id`: Session identifier
- `video_paths`: List of video paths in order

### 5. estimate_cost(num_images, total_video_duration)
Estimates generation costs.

**Parameters:**
- `num_images`: Number of images to generate
- `total_video_duration`: Total video length in seconds

### 6. save_workflow_state(state_json)
Saves workflow for later resumption.

### 7. load_workflow_state(session_id)
Loads a previously saved workflow.

## Key Constraints

### Veo 3.1 Limitations
- **Fixed duration**: Always generates exactly 8 seconds per segment
- **No quality control**: Video quality is automatic
- **No resolution control**: Resolution is automatic
- **Generation time**: ~30-60 seconds per segment

### Scene Planning
- Videos must be broken into 8-second scenes
- For a 25-second video: create 4 scenes (8s + 8s + 8s + 1s)
- Each scene needs a unique scene_id and prompt

### Continuity
- Previous scene's end-frame becomes next scene's start-frame
- This ensures smooth transitions between segments
- Images must be generated before videos

## Pricing

**Approximate costs (subject to change):**
- **Images**: $0.10 per image
- **Videos**: $0.40 per second

**Image count calculation:**
- First scene: 2 images (start + end)
- Each additional scene: 1 image (end only)
- Formula: (num_scenes + 1) images total

**Example costs:**
- 10-second video (2 scenes, 3 images): ~$4.30 ($0.30 images + $4.00 videos)
- 20-second video (3 scenes, 4 images): ~$8.40 ($0.40 images + $8.00 videos)
- 60-second video (8 scenes, 9 images): ~$24.90 ($0.90 images + $24.00 videos)

Always call `estimate_cost` before generation!

## Best Practices

### Scene Planning
1. **Break down longer videos** into logical 8-second segments
2. **Describe action clearly** for each scene
3. **Plan transitions** between scenes for narrative flow
4. **Create detailed prompts** for both images and videos

### Cost Management
1. **Always estimate first** before generating
2. **Confirm with user** before expensive operations
3. **Start small** for testing (10-20 seconds)
4. **Scale up** once workflow is proven

### Error Handling
1. **Save state** for long workflows
2. **Check success status** of each tool call
3. **Communicate errors** clearly to users
4. **Resume from saved state** if interrupted

## File Structure

Generated assets are stored in:
```
~/.claudio/sessions/<session_id>/
├── images/
│   ├── scene_1_start.png  ← Start-frame for first scene
│   ├── scene_1_end.png
│   ├── scene_2_end.png
│   └── scene_3_end.png
├── videos/
│   ├── scene_1.mp4
│   ├── scene_2.mp4
│   └── scene_3.mp4
├── final.mp4
└── state.json
```

## Troubleshooting

### FFmpeg Not Found
```bash
brew install ffmpeg  # macOS
sudo apt-get install ffmpeg  # Ubuntu
```

### API Key Errors
Ensure `.env` file contains:
```
GOOGLE_API_KEY=your_google_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### Session Not Found
Use `create_session_id()` before other operations, or use `load_workflow_state()` to resume.

### Generation Timeout
Long videos (60+ seconds) may take 30+ minutes. Save state periodically.

## Examples

### Short Video (10 seconds)
```
User: Make a 10-second coffee commercial

Claude:
1. Calls create_session_id() → session_123
2. Plans 2 scenes (8s + 2s)
3. Calls estimate_cost(2, 10.0) → $4.20
4. Generates 2 images
5. Generates 2 videos
6. Calls concatenate_videos() → final.mp4
```

### Multi-scene Video (30 seconds)
```
User: Create a 30-second product demo

Claude:
1. Creates session
2. Plans 4 scenes (8s + 8s + 8s + 6s)
3. Estimates cost → $12.40
4. Generates 4 images
5. Generates 4 videos (using previous end-frames as start-frames)
6. Concatenates → final.mp4
```

## Technical Details

- **MCP Server**: FastMCP-based stdio server
- **Transport**: JSON-RPC over stdin/stdout
- **API Clients**: Google GenAI SDK for Veo 3.1 and Imagen
- **Video Processing**: FFmpeg for concatenation
- **State Management**: JSON-based persistence

## Limitations

1. **No real-time preview** - Generate first, then view
2. **No editing** - Must regenerate entire scenes
3. **Sequential generation** - No parallel scene generation in MCP
4. **8-second constraint** - Cannot generate longer segments
5. **No audio control** - Veo generates with or without audio automatically

## Future Enhancements

Potential improvements:
- Progress tracking for long operations
- Scene preview before generation
- Editing individual scenes
- Template library for common video types
- Batch operations for parallel generation
- Asset management and reuse