# Enhanced YouTube Video Clipper API v2.0

A powerful REST API for downloading YouTube videos, creating custom clips, and extracting audio with advanced customization options. Built for easy integration and deployment on RapidAPI.

## New Features in v2.0

- **Audio Extraction**: Extract MP3 audio from videos or clips
- **Audio Clipping**: Create custom audio clips with precise timing
- **Subtitle Support**: Download videos with synchronized subtitles
- **Multiple Download Modes**: Fast, Balanced, and Precise processing
- **Enhanced Quality Control**: Separate video and audio quality settings
- **Custom Format Support**: Advanced yt-dlp format selectors
- **Windows Compatibility**: Full support for Windows deployment
- **Improved Error Handling**: Better validation and error messages

## Features

- Download full YouTube videos in various qualities (360p to 4K)
- Create custom video and audio clips with precise start/end times
- Extract high-quality MP3 audio from videos
- Download videos with embedded or separate subtitles
- Multiple processing modes for speed vs quality optimization
- Extract comprehensive video metadata
- Automatic temporary file cleanup
- Production-ready with comprehensive error handling
- RapidAPI compatible with proper header validation

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
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
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
  - `fast`: Stream copying - fastest but may have sync issues
  - `balanced`: Fast encode - good balance of speed and quality
  - `precise`: Full re-encode - slowest but most reliable
  - `audio_only`: Audio extraction only
  - Default: `balanced`
- `start` (integer, optional): Start time in seconds for clipping
- `end` (integer, optional): End time in seconds for clipping
- `extract_audio` (boolean, optional): Extract audio as MP3
  - Default: `false`
- `include_subtitles` (boolean, optional): Include subtitles
  - Default: `false`
- `subtitle_languages` (array, optional): Subtitle languages to download
  - Example: `["en", "es", "fr"]`
  - Default: `["en"]`
- `thumbnail` (boolean, optional): Download thumbnail image
  - Default: `false`
- `metadata` (boolean, optional): Include video metadata
  - Default: `true`
- `custom_format` (string, optional): Custom yt-dlp format selector

### GET /health
Health check endpoint for monitoring API status.

## Usage Examples

### Get Video Information
```bash
curl -X POST /info \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: your-api-key" \
  -H "X-RapidAPI-Host: your-api-host" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

### Download Full Video (720p)
```bash
curl -X POST /download \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: your-api-key" \
  -H "X-RapidAPI-Host: your-api-host" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "video_quality": "720p", "download_mode": "balanced"}' \
  --output video.mp4
```

### Create Video Clip (30 seconds)
```bash
curl -X POST /download \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: your-api-key" \
  -H "X-RapidAPI-Host: your-api-host" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "start": 30, "end": 60, "video_quality": "720p", "download_mode": "fast"}' \
  --output clip.mp4
```

### Extract High-Quality Audio
```bash
curl -X POST /download \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: your-api-key" \
  -H "X-RapidAPI-Host: your-api-host" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "extract_audio": true, "audio_quality": "320"}' \
  --output audio.mp3
```

### Create Audio Clip
```bash
curl -X POST /download \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: your-api-key" \
  -H "X-RapidAPI-Host: your-api-host" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "start": 30, "end": 60, "extract_audio": true, "audio_quality": "320"}' \
  --output audio_clip.mp3
```

### Download with Subtitles (Returns ZIP)
```bash
curl -X POST /download \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: your-api-key" \
  -H "X-RapidAPI-Host: your-api-host" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "video_quality": "720p", "include_subtitles": true, "subtitle_languages": ["en"]}' \
  --output video_with_subs.zip
```

## Response Formats

### Success Response (Download)
Returns the media file as a binary download:
- **Video/Audio only**: Direct MP4/MP3 file
- **With subtitles/thumbnails**: ZIP file containing all files

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
  "error": "Error description"
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

### Fast Mode
- Uses stream copying for maximum speed
- Maintains original quality
- May have minor sync issues with some videos
- Best for: Long clips, when speed is priority

### Balanced Mode (Recommended)
- Fast encoding with good quality
- Good balance of speed and reliability
- Suitable for most use cases
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

## Local Development

### Prerequisites
- **Python 3.10+** (recommended 3.11)
- **FFmpeg** (for video/audio processing)
- **Git**

### Installation

**Windows:**
```bash
# Install Python 3.10+ and FFmpeg
choco install python ffmpeg  # Using Chocolatey
# or download from python.org and ffmpeg.org

# Clone and setup
git clone https://github.com/yourusername/enhanced-youtube-clipper.git
cd enhanced-youtube-clipper
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Linux/macOS:**
```bash
# Install dependencies
sudo apt install python3.10 ffmpeg  # Ubuntu/Debian
# or: brew install python@3.10 ffmpeg  # macOS

# Clone and setup
git clone https://github.com/yourusername/enhanced-youtube-clipper.git
cd enhanced-youtube-clipper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running Locally

**Development:**
```bash
python api.py
```

**Production (Windows):**
```bash
waitress-serve --host=0.0.0.0 --port=5000 --threads=4 api:app
```

**Production (Linux/macOS):**
```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 300 api:app
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
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'

# Test audio extraction
curl -X POST http://localhost:5000/download \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: test-key" \
  -H "X-RapidAPI-Host: localhost" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "extract_audio": true}' \
  --output test.mp3
```

## Deployment

### Requirements
- **Python 3.10+**
- **FFmpeg**
- **Waitress** (Windows) or **Gunicorn** (Linux/macOS)

### Environment Variables
- `PORT`: Server port (default: 5000)
- `MAX_WORKERS`: Number of worker processes
- `DOWNLOAD_FOLDER`: Temporary files directory

### Production Deployment
The API supports deployment on major cloud platforms:
- **Heroku**: Use Procfile with buildpacks
- **Railway**: Direct deployment with automatic builds
- **Render**: Web service with auto-deploy
- **DigitalOcean App Platform**: Container or buildpack deployment
- **AWS/Azure/GCP**: Container deployment recommended

### Docker Deployment
```dockerfile
FROM python:3.11-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY api.py .
EXPOSE 5000

CMD ["waitress-serve", "--host=0.0.0.0", "--port=5000", "--threads=4", "api:app"]
```

## Error Handling

Comprehensive error handling for common scenarios:
- Invalid YouTube URLs
- Unsupported video formats  
- Invalid quality parameters
- Invalid clip timing (start >= end, exceeds duration)
- Missing required headers
- Video processing errors
- Network timeouts
- FFmpeg conversion failures

## Performance Optimization

- **Automatic cleanup**: Temporary files removed after 1 hour
- **Concurrent processing**: Multi-threaded request handling
- **Memory management**: Efficient file streaming
- **Format optimization**: Automatic best format selection
- **Error recovery**: Graceful handling of failed downloads

## Technology Stack

- **Flask 3.1.0**: Modern web framework
- **yt-dlp 2025.8.20**: Latest YouTube processing library
- **FFmpeg**: Professional video/audio processing
- **Waitress/Gunicorn**: Production WSGI servers
- **Python 3.10+**: Modern Python features

## API Changelog

### v2.0.0 (Current)
- Audio extraction and clipping
- Subtitle support with ZIP packaging
- Multiple download modes
- Enhanced quality controls
- Windows compatibility
- Custom format selectors
- Improved error handling

### v1.0.0
- Basic video downloading
- Video clipping functionality
- Quality selection
- RapidAPI integration

## Terms of Use

This API is provided for **educational and personal use only**. Users are responsible for:

- Complying with YouTube's Terms of Service
- Respecting applicable copyright laws
- Only downloading content you have permission to access
- Using content that is in the public domain or fair use

**The API provider does not endorse or encourage any violation of terms of service or copyright infringement.**

## License

MIT License - see LICENSE file for details

## Support

- **API Issues**: Contact support through RapidAPI platform
- **Documentation**: Available on RapidAPI marketplace
- **Technical Support**: Use RapidAPI messaging system
- **Feature Requests**: Submit through RapidAPI feedback

## Acknowledgments

- **yt-dlp team**: For the excellent YouTube processing library
- **FFmpeg project**: For powerful media processing capabilities
- **Flask community**: For the robust web framework
- **Contributors**: Thanks to all who helped improve this API

---

**Made with care for developers who need reliable YouTube processing**
