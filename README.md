# YouTube Video Clipper API

A REST API for downloading YouTube videos and creating custom clips with multiple quality options. Built for easy integration and deployment on RapidAPI.

## Features

- Download full YouTube videos in various qualities
- Create custom video clips with precise start/end times
- Multiple quality options from 360p to 4K
- Fast and precise clipping modes
- Extract video metadata without downloading
- Automatic temporary file cleanup
- Production-ready with comprehensive error handling
- RapidAPI compatible with proper header validation

## API Endpoints

### GET /
Returns API information, supported features, and current limits.

### POST /info
Extract video metadata without downloading the video.

**Parameters:**
- `url` (string, required): YouTube video URL

**Example:**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

### POST /download
Download a full video or create a custom clip.

**Parameters:**
- `url` (string, required): YouTube video URL
- `quality` (string, optional): Video quality preference
  - Options: `best`, `2160p`, `1440p`, `1080p`, `720p`, `480p`, `360p`
  - Default: `best`
- `start` (integer, optional): Start time in seconds for clipping
- `end` (integer, optional): End time in seconds for clipping
- `fast_clip` (boolean, optional): Use fast clipping mode (may be less precise but faster)
  - Default: `false`

**Examples:**

Download full video:
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "quality": "720p"
}
```

Create a 30-second clip:
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "quality": "720p",
  "start": 30,
  "end": 60,
  "fast_clip": true
}
```

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

### Download Video
```bash
curl -X POST /download \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: your-api-key" \
  -H "X-RapidAPI-Host: your-api-host" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "quality": "720p"}' \
  --output video.mp4
```

### Create Custom Clip
```bash
curl -X POST /download \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: your-api-key" \
  -H "X-RapidAPI-Host: your-api-host" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "start": 10, "end": 40, "quality": "720p"}' \
  --output clip.mp4
```

## Response Formats

### Success Response (Download)
Returns the video file as a binary download with appropriate headers.

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
    "description": "Video description...",
    "thumbnail": "https://...",
    "webpage_url": "https://..."
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

- Maximum clip duration: 30 minutes
- Maximum video duration: 4 hours
- Minimum clip duration: 1 second
- Supported domains: youtube.com, youtu.be
- Temporary files are automatically cleaned up after 2 hours

## Clipping Modes

### Precise Mode (Default)
- Re-encodes video for exact timing
- Perfect quality and synchronization
- Slower processing time
- Recommended for most use cases

### Fast Mode
- Uses stream copying for speed
- Much faster processing
- Maintains original quality
- Good for longer clips where speed is important

## Local Development

### Prerequisites
- Python 3.10 or higher
- FFmpeg (for video processing)

### Installation
```bash
git clone https://github.com/josearruticuanda/yt_clipper.git
cd yt_clipper
pip install -r requirements.txt
```

### Running Locally
```bash
python api.py
```

The API will be available at `http://localhost:5000`

### Testing
```bash
# Test API info
curl -X GET http://localhost:5000/

# Test video info
curl -X POST http://localhost:5000/info \
  -H "Content-Type: application/json" \
  -H "X-RapidAPI-Key: test-key" \
  -H "X-RapidAPI-Host: test-host" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

## Deployment

### Requirements
- Python 3.10+
- FFmpeg
- Gunicorn (for production)

### Environment Variables
- `PORT`: Server port (default: 5000)

### Production Deployment
The API is designed to work with major cloud platforms:
- Heroku
- Railway
- Render
- DigitalOcean App Platform

## Error Handling

The API provides comprehensive error handling for common scenarios:
- Invalid YouTube URLs
- Unsupported video formats
- Invalid quality parameters
- Invalid clip timing
- Missing required headers
- Video processing errors

## Technology Stack

- **Flask**: Web framework
- **yt-dlp**: YouTube video processing
- **FFmpeg**: Video encoding and clipping
- **Gunicorn**: Production WSGI server

## License

MIT License

## Contributing

Issues and pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## Support

For API support and questions, please refer to the RapidAPI documentation or create an issue in this repository.
