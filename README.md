# Enhanced YouTube Video Clipper API

A powerful REST API for downloading YouTube videos, creating custom clips, and extracting audio with advanced customization options.

## Features

- **Audio Extraction**: Extract MP3 audio from videos or clips
- **Audio Clipping**: Create custom audio clips with precise timing
- **Subtitle Support**: Download videos with synchronized subtitles
- **Multiple Download Modes**: Fast (default), Balanced, and Precise processing
- **Enhanced Quality Control**: Separate video and audio quality settings
- **Docker Ready**: Containerized deployment with all dependencies
- **Improved Error Handling**: Better validation and user-friendly error messages
- **Auto-Download in Browser**: Files automatically download in browser

## Core Functionality

- Download full YouTube videos in various qualities (360p to 4K)
- Create custom video and audio clips with precise start/end times
- Extract high-quality MP3 audio from videos
- Download videos with embedded or separate subtitles
- Multiple processing modes optimized for speed vs quality
- Automatic temporary file cleanup
- Production-ready with comprehensive error handling
- Fast processing by default for reduced timeout risk

## Quick Start

```bash
docker build -t yt-clipper .
docker run -it --rm -p 5000:5000 yt-clipper
```

The API will be available at `http://localhost:5000`

### Testing
```bash
# Health check
curl http://localhost:5000/health

# Test video info
curl -X POST http://localhost:5000/info \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: test-key" \
  -H "X-RapidAPI-Host: localhost" \
  -d '{"url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"}'

# Test audio extraction
curl -X POST http://localhost:5000/download \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: test-key" \
  -H "X-RapidAPI-Host: localhost" \
  -d '{"url": "https://www.youtube.com/watch?v=jNQXAC9IVRw", "extract_audio": true}' \
  --output test.mp3
```

## API Endpoints

### GET /
Returns API information, supported features, and current limits.

### POST /info
Extract detailed video metadata without downloading.

**Parameters:**
- `url` (string, required): YouTube video URL

**Example:**
```json
{
  "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"
}
```

### POST /formats
Get all available video formats and quality options for a specific video.

**Parameters:**
- `url` (string, required): YouTube video URL

### POST /download
Download a full video, create clips, or extract audio with advanced options.

**Parameters:**
- `url` (string, required): YouTube video URL
- `video_quality` (string, optional): Video quality preference
  - Options: `best`, `2160p`, `1440p`, `1080p`, `720p`, `480p`, `360p`, `worst`
  - Default: `best`
- `audio_quality` (string, optional): Audio quality preference
  - Options: `best`, `320`, `192`, `128`, `worst` (kbps)
  - Default: `best`
- `download_mode` (string, optional): Processing mode
  - `fast`: Stream copying - fastest, recommended (DEFAULT)
  - `balanced`: Fast encode - good balance of speed and quality
  - `precise`: Full re-encode - slowest but most reliable
  - `audio_only`: Audio extraction only
  - Default: `fast`
- `start` (integer, optional): Start time in seconds for clipping
- `end` (integer, optional): End time in seconds for clipping
- `extract_audio` (boolean, optional): Extract audio as MP3
  - Default: `false`
- `include_subtitles` (boolean, optional): Include subtitles
  - Default: `false`
- `subtitle_languages` (array, optional): Subtitle languages to download
  - Example: `["en", "es", "fr"]`
  - Default: `["en"]`

### GET /health
Health check endpoint for monitoring API status.

## Usage Examples

### Get Video Information
```bash
curl -X POST /info \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: your-api-key" \
  -H "X-RapidAPI-Host: your-api-host" \
  -d '{"url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"}'
```

### Download Full Video (720p, Fast Mode)
```bash
curl -X POST /download \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: your-api-key" \
  -H "X-RapidAPI-Host: your-api-host" \
  -d '{"url": "https://www.youtube.com/watch?v=jNQXAC9IVRw", "video_quality": "720p"}' \
  --output video.mp4
```

### Create Video Clip (Fast Mode Default)
```bash
curl -X POST /download \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: your-api-key" \
  -H "X-RapidAPI-Host: your-api-host" \
  -d '{"url": "https://www.youtube.com/watch?v=jNQXAC9IVRw", "start": 5, "end": 15, "video_quality": "720p"}' \
  --output clip.mp4
```

### Extract High-Quality Audio
```bash
curl -X POST /download \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: your-api-key" \
  -H "X-RapidAPI-Host: your-api-host" \
  -d '{"url": "https://www.youtube.com/watch?v=jNQXAC9IVRw", "extract_audio": true, "audio_quality": "320"}' \
  --output audio.mp3
```

### Create Audio Clip
```bash
curl -X POST /download \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: your-api-key" \
  -H "X-RapidAPI-Host: your-api-host" \
  -d '{"url": "https://www.youtube.com/watch?v=jNQXAC9IVRw", "start": 5, "end": 15, "extract_audio": true, "audio_quality": "320"}' \
  --output audio_clip.mp3
```

### Download with Subtitles (Returns ZIP)
```bash
curl -X POST /download \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: your-api-key" \
  -H "X-RapidAPI-Host: your-api-host" \
  -d '{"url": "https://www.youtube.com/watch?v=jNQXAC9IVRw", "video_quality": "720p", "include_subtitles": true, "subtitle_languages": ["en"]}' \
  --output video_with_subs.zip
```

## Response Formats

### Success Response (Download)
Returns the media file as a binary download with automatic browser download:
- **Video/Audio only**: Direct MP4/MP3 file download
- **With subtitles**: ZIP file containing all files

### Success Response (Info)
```json
{
  "status": "success",
  "video_info": {
    "title": "Video Title",
    "duration": 212,
    "duration_formatted": "00:03:32",
    "uploader": "Channel Name",
    "upload_date": "20231201",
    "view_count": 1000000,
    "like_count": 50000,
    "description": "Video description...",
    "thumbnail": "https://...",
    "webpage_url": "https://...",
    "available_qualities": ["1080p", "720p", "480p", "360p"],
    "has_subtitles": true,
    "subtitle_languages": ["en", "es", "fr"],
    "chapters": [],
    "tags": ["music", "video", "entertainment"]
  }
}
```

### Error Response
```json
{
  "error": "YouTube is blocking access to this video. This can happen with popular music videos or content with strict download restrictions. Try a different video."
}
```

## Limits and Constraints

- **Maximum clip duration**: 1 hour
- **Maximum video duration**: 5 hours
- **Minimum clip duration**: 1 second
- **File cleanup**: Automatic cleanup after 1 hour
- **Supported domains**: youtube.com, youtu.be, music.youtube.com
- **Request size limit**: 32MB

## Download Modes

### Fast Mode (DEFAULT)
- Uses stream copying for maximum speed
- Maintains original quality
- Significantly reduces processing time and timeout risk
- May have minor sync issues with some videos
- Best for: long clips, when speed is priority

### Balanced Mode
- Fast encoding with good quality
- Good balance of speed and reliability
- Suitable for most use cases where speed isn't critical
- Best for: General purpose downloading

### Precise Mode
- Full re-encoding for perfect quality
- Slower processing time
- Highest reliability and quality
- Best for: Short clips, when quality is critical

### Audio Only Mode
- Optimized for audio extraction
- Automatic audio quality optimization
- Fast processing
- Best for: Music, podcasts, audio content

## Error Handling

Comprehensive error handling for common scenarios:
- Invalid YouTube URLs with helpful suggestions
- Video access blocked by YouTube with clear explanations
- Unsupported video formats  
- Invalid quality parameters
- Invalid clip timing (start >= end, exceeds duration)
- Missing required headers
- Video processing errors
- Network timeouts
- FFmpeg conversion failures

## Performance Optimization

- **Fast Mode Default**: Stream copying for maximum speed
- **Automatic cleanup**: Temporary files removed after 1 hour
- **Concurrent processing**: Multi-threaded request handling
- **Memory management**: Efficient file streaming
- **Format optimization**: Automatic best format selection
- **Error recovery**: Graceful handling of failed downloads

## Technology Stack

- **Flask 3.1.0**: Modern web framework
- **yt-dlp 2025.8.20**: Latest YouTube processing library
- **FFmpeg**: Professional video/audio processing
- **Python 3.11**: Modern Python features
- **Docker**: Containerized deployment

## API Changelog

### Current Version
- Fast mode set as default
- Improved error messages for blocked videos
- Auto-download functionality for browser testing
- Enhanced validation and user feedback
- Audio extraction and clipping
- Subtitle support with ZIP packaging
- Multiple download modes
- Enhanced quality controls
- Comprehensive error handling

## Terms of Use

This API is provided for **educational and personal use only**. Users are responsible for:

- Complying with YouTube's Terms of Service
- Respecting applicable copyright laws
- Only downloading content you have permission to access
- Using content that is in the public domain or fair use

**The API provider does not endorse or encourage any violation of terms of service or copyright infringement.**

## License

MIT License - see LICENSE file for details
---
