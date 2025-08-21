import os
import tempfile
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse

import yt_dlp
from flask import Flask, send_file, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CONFIGURATION
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request size

# Constants
DOWNLOAD_FOLDER = "temp_downloads"
MAX_FILE_AGE_HOURS = 2
MAX_CLIP_DURATION = 1800  # 30 minutes max for reliable API performance
MIN_CLIP_DURATION = 1     # 1 second min clip duration
MAX_VIDEO_DURATION = 14400  # 4 hours max total video duration

# Ensure download folder exists
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


class VideoDownloadError(Exception):
    """Custom exception for video download errors"""
    pass


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def validate_rapidapi_headers() -> Tuple[bool, Optional[Dict], int]:
    """
    Validate RapidAPI headers for authentication.
    
    Returns:
        Tuple of (is_valid, error_response, status_code)
    """
    rapidapi_key = request.headers.get('X-RapidAPI-Key')
    rapidapi_host = request.headers.get('X-RapidAPI-Host')
    
    if not rapidapi_key or not rapidapi_host:
        return False, {
            "error": "Authentication failed",
            "message": "X-RapidAPI-Key and X-RapidAPI-Host headers are required"
        }, 401
    
    return True, None, 200


def validate_youtube_url(url: str) -> bool:
    """
    Validate if the provided URL is a valid YouTube URL.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid YouTube URL, False otherwise
    """
    if not url:
        return False
    
    try:
        parsed = urlparse(url)
        valid_domains = ['youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com']
        return parsed.netloc.lower() in valid_domains
    except Exception:
        return False


def validate_clip_times(start: Optional[int], end: Optional[int], duration: int) -> None:
    """
    Validate clip start and end times.
    
    Args:
        start: Start time in seconds
        end: End time in seconds
        duration: Video duration in seconds
        
    Raises:
        ValidationError: If validation fails
    """
    # Check if video duration exceeds maximum allowed
    if duration > MAX_VIDEO_DURATION:
        raise ValidationError(f"Video duration ({format_duration(duration)}) exceeds maximum allowed duration ({format_duration(MAX_VIDEO_DURATION)})")
    
    if start is None or end is None:
        return
    
    if not isinstance(start, int) or not isinstance(end, int):
        raise ValidationError("Start and end times must be integers")
    
    if start < 0 or end < 0:
        raise ValidationError("Start and end times must be non-negative")
    
    if start >= end:
        raise ValidationError("Start time must be less than end time")
    
    if end > duration:
        raise ValidationError(f"End time ({format_duration(end)}) exceeds video duration ({format_duration(duration)})")
    
    clip_duration = end - start
    if clip_duration < MIN_CLIP_DURATION:
        raise ValidationError(f"Clip duration must be at least {MIN_CLIP_DURATION} second(s)")
    
    if clip_duration > MAX_CLIP_DURATION:
        raise ValidationError(f"Clip duration ({format_duration(clip_duration)}) cannot exceed maximum allowed ({format_duration(MAX_CLIP_DURATION)})")


def force_cleanup_all_files() -> None:
    """Remove ALL files from temp folder to prevent storage buildup."""
    try:
        if not os.path.exists(DOWNLOAD_FOLDER):
            os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
            return
            
        cleaned_count = 0
        for filename in os.listdir(DOWNLOAD_FOLDER):
            file_path = os.path.join(DOWNLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    cleaned_count += 1
                    logger.info(f"Cleaned up file: {filename}")
                except Exception as file_error:
                    logger.error(f"Error removing file {filename}: {file_error}")
        
        logger.info(f"Cleanup completed: {cleaned_count} files removed")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


def cleanup_old_files() -> None:
    """Remove files older than MAX_FILE_AGE_HOURS to prevent storage buildup."""
    try:
        cutoff_time = datetime.now() - timedelta(hours=MAX_FILE_AGE_HOURS)
        
        for filename in os.listdir(DOWNLOAD_FOLDER):
            file_path = os.path.join(DOWNLOAD_FOLDER, filename)
            
            if os.path.isfile(file_path):
                file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_modified < cutoff_time:
                    os.remove(file_path)
                    logger.info(f"Cleaned up old file: {filename}")
                    
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing/replacing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length and strip whitespace
    return filename.strip()[:100]


def extract_video_info(url: str) -> Dict[str, Any]:
    """
    Extract video information from YouTube URL.
    
    Args:
        url: YouTube video URL
        
    Returns:
        Dictionary containing video information
        
    Raises:
        VideoDownloadError: If extraction fails
    """
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extractaudio': False,
            'extract_flat': False
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'upload_date': info.get('upload_date'),
                'view_count': info.get('view_count', 0),
                'description': info.get('description', ''),
                'thumbnail': info.get('thumbnail'),
                'webpage_url': info.get('webpage_url', url)
            }
            
    except Exception as e:
        logger.error(f"Failed to extract video info: {e}")
        raise VideoDownloadError(f"Failed to extract video information: {str(e)}")


def format_duration(seconds: int) -> str:
    """
    Format duration from seconds to HH:MM:SS format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds <= 0:
        return "00:00:00"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def get_format_selector(quality: str) -> str:
    """
    Get yt-dlp format selector based on quality preference.
    
    Args:
        quality: Quality preference (best, 2160p, 1440p, 1080p, 720p, 480p, 360p)
        
    Returns:
        Format selector string for yt-dlp
    """
    quality_formats = {
        'best': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
        '2160p': 'bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best[height<=2160]',
        '1440p': 'bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1440]+bestaudio/best[height<=1440]',
        '1080p': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        '720p': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]',
        '480p': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]',
        '360p': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best[height<=360]'
    }
    
    return quality_formats.get(quality.lower(), quality_formats['best'])


def validate_quality(quality: str) -> str:
    """
    Validate and normalize quality parameter.
    
    Args:
        quality: Quality string to validate
        
    Returns:
        Normalized quality string
        
    Raises:
        ValidationError: If quality is invalid
    """
    valid_qualities = ['best', '2160p', '1440p', '1080p', '720p', '480p', '360p']
    
    if quality is None:
        return 'best'
    
    quality = quality.lower().strip()
    
    if quality not in valid_qualities:
        raise ValidationError(f"Invalid quality '{quality}'. Supported qualities: {', '.join(valid_qualities)}")
    
    return quality


def download_video(url: str, start_time: Optional[int] = None, 
                  end_time: Optional[int] = None, quality: str = 'best', fast_clip: bool = False) -> str:
    """
    Download video from YouTube with optional clipping and quality selection.
    
    Args:
        url: YouTube video URL
        start_time: Start time in seconds for clipping
        end_time: End time in seconds for clipping
        quality: Video quality preference (best, 2160p, 1440p, 1080p, 720p, 480p, 360p)
        fast_clip: If True, use fast stream copying (may have video issues but much faster)
        
    Returns:
        Path to downloaded file
        
    Raises:
        VideoDownloadError: If download fails
    """
    try:
        # Get video info first
        info = extract_video_info(url)
        video_title = sanitize_filename(info['title'])
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{video_title}_{timestamp}.mp4"
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)
        
        # Configure download options
        format_selector = get_format_selector(quality)
        ydl_opts = {
            'format': format_selector,
            'outtmpl': file_path,
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'writesubtitles': False,
            'writeautomaticsub': False
        }
        
        # Add clipping if specified
        if start_time is not None and end_time is not None:
            if fast_clip:
                # Fast clipping using FFmpeg with stream copying but keyframe-aware cutting
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }]
                
                # Use stream copying with keyframe seeking for speed
                ydl_opts['postprocessor_args'] = [
                    '-ss', str(start_time),
                    '-t', str(end_time - start_time),
                    '-c:v', 'copy',  # Copy video stream (faster)
                    '-c:a', 'copy',  # Copy audio stream (faster) 
                    '-copyts',       # Copy timestamps
                    '-avoid_negative_ts', 'make_zero',
                    '-fflags', '+genpts'  # Generate presentation timestamps
                ]
                
                logger.info(f"Fast clipping {quality} from {format_duration(start_time)} to {format_duration(end_time)} (stream copy mode)")
            else:
                # Slow but reliable clipping with re-encoding
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }]
                
                # Add FFmpeg arguments for precise cutting
                ydl_opts['postprocessor_args'] = [
                    '-ss', str(start_time),
                    '-t', str(end_time - start_time),  # Duration instead of end time
                    '-c:v', 'libx264',  # Re-encode video to ensure proper cutting
                    '-c:a', 'aac',      # Re-encode audio
                    '-avoid_negative_ts', 'make_zero'  # Fix timing issues
                ]
                
                logger.info(f"Precise clipping {quality} from {format_duration(start_time)} to {format_duration(end_time)} (duration: {format_duration(end_time - start_time)})")
        else:
            logger.info(f"Downloading full video in {quality} quality")
        
        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Verify file was created
        if not os.path.exists(file_path):
            raise VideoDownloadError("Video file was not created")
        
        return file_path
        
    except VideoDownloadError:
        raise
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise VideoDownloadError(f"Download failed: {str(e)}")


# ROUTES

@app.route("/", methods=["GET"])
def home():
    """API information endpoint."""
    return jsonify({
        "service": "YouTube Video Clipper API",
        "version": "1.0.0",
        "description": "Download full or clipped videos from YouTube",
        "endpoints": {
            "/download": "POST - Download video with optional clipping",
            "/info": "POST - Get video information without downloading",
            "/health": "GET - Health check"
        },
        "parameters": {
            "url": "YouTube video URL (required)",
            "start": "Start time in seconds for clipping (optional)",
            "end": "End time in seconds for clipping (optional)",
            "quality": "Video quality: best, 2160p, 1440p, 1080p, 720p, 480p, 360p (optional, default: best)",
            "fast_clip": "Use fast clipping (may have video issues, default: false)"
        },
        "limits": {
            "max_clip_duration": f"{format_duration(MAX_CLIP_DURATION)}",
            "min_clip_duration": f"{MIN_CLIP_DURATION} second",
            "max_video_duration": f"{format_duration(MAX_VIDEO_DURATION)}",
            "supported_qualities": ["best", "2160p", "1440p", "1080p", "720p", "480p", "360p"],
            "supported_domains": ["youtube.com", "youtu.be"]
        }
    })


@app.route("/download", methods=["POST"])
def download_video_endpoint():
    """Download video endpoint with optional clipping."""
    # Validate RapidAPI headers
    is_valid, error_response, status_code = validate_rapidapi_headers()
    if not is_valid:
        return jsonify(error_response), status_code
    
    # Clean up ALL files before each download to prevent storage issues
    force_cleanup_all_files()
    
    try:
        # Parse request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        url = data.get("url")
        start_time = data.get("start")
        end_time = data.get("end")
        quality = data.get("quality", "best")
        fast_clip = data.get("fast_clip", False)
        
        # Validate inputs
        if not validate_youtube_url(url):
            return jsonify({"error": "Invalid YouTube URL"}), 400
        
        try:
            quality = validate_quality(quality)
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        
        # Get video info and validate clip times
        try:
            info = extract_video_info(url)
            validate_clip_times(start_time, end_time, info['duration'])
        except (ValidationError, VideoDownloadError) as e:
            return jsonify({"error": str(e)}), 400
        
        # Download video
        file_path = download_video(url, start_time, end_time, quality, fast_clip)
        filename = os.path.basename(file_path)
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )
        
    except VideoDownloadError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500


@app.route("/info", methods=["POST"])
def get_video_info_endpoint():
    """Get video information endpoint."""
    # Validate RapidAPI headers
    is_valid, error_response, status_code = validate_rapidapi_headers()
    if not is_valid:
        return jsonify(error_response), status_code
    
    try:
        # Parse request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        url = data.get("url")
        
        # Validate URL
        if not validate_youtube_url(url):
            return jsonify({"error": "Invalid YouTube URL"}), 400
        
        # Extract video information
        info = extract_video_info(url)
        
        # Format response
        response_data = {
            "title": info['title'],
            "duration": info['duration'],
            "duration_formatted": format_duration(info['duration']),
            "uploader": info['uploader'],
            "upload_date": info['upload_date'],
            "view_count": info['view_count'],
            "description": info['description'][:500] + "..." if len(info['description']) > 500 else info['description'],
            "thumbnail": info['thumbnail'],
            "webpage_url": info['webpage_url']
        }
        
        return jsonify({
            "status": "success",
            "video_info": response_data
        })
        
    except VideoDownloadError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "YouTube Clipper API",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "Request payload too large"}), 413


@app.errorhandler(500)
def internal_server_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    # For production, use a WSGI server like gunicorn
    # For development/testing only
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
