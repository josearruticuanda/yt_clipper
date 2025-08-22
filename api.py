import os
import tempfile
import logging
import asyncio
import zipfile
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List
from urllib.parse import urlparse
from dataclasses import dataclass
from enum import Enum

import yt_dlp
from flask import Flask, send_file, request, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CONFIGURATION
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max request size

# Constants
DOWNLOAD_FOLDER = "temp_downloads"
MAX_FILE_AGE_HOURS = 1
MAX_CLIP_DURATION = 3600  # 1 hour max for reliable API performance
MIN_CLIP_DURATION = 1     # 1 second min clip duration
MAX_VIDEO_DURATION = 18000  # 5 hours max total video duration

# Ensure download folder exists
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


class DownloadMode(Enum):
    """Download modes for different use cases"""
    FAST = "fast"          # Stream copying, fastest but may have issues
    BALANCED = "balanced"  # Good balance of speed and quality
    PRECISE = "precise"    # Re-encoding, slowest but most reliable
    AUDIO_ONLY = "audio_only"  # Audio extraction only


class VideoQuality(Enum):
    """Video quality options"""
    BEST = "best"
    UHD_4K = "2160p"
    QHD_2K = "1440p"
    FHD = "1080p"
    HD = "720p"
    SD = "480p"
    LD = "360p"
    WORST = "worst"


class AudioQuality(Enum):
    """Audio quality options"""
    BEST = "best"
    HIGH = "320"    # 320 kbps
    MEDIUM = "192"  # 192 kbps
    LOW = "128"     # 128 kbps
    WORST = "worst"


@dataclass
class DownloadOptions:
    """Configuration class for download options"""
    url: str
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    video_quality: VideoQuality = VideoQuality.BEST
    audio_quality: AudioQuality = AudioQuality.BEST
    download_mode: DownloadMode = DownloadMode.BALANCED
    extract_audio: bool = False
    include_subtitles: bool = False
    subtitle_languages: List[str] = None
    thumbnail: bool = False
    metadata: bool = True
    custom_format: Optional[str] = None


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
    # Temporarily disable authentication for RapidAPI testing
    
    # rapidapi_key = request.headers.get('X-RapidAPI-Key')
    # rapidapi_host = request.headers.get('X-RapidAPI-Host')
    
    # if not rapidapi_key or not rapidapi_host:
    #     return False, {
    #         "error": "Authentication failed",
    #         "message": "X-RapidAPI-Key and X-RapidAPI-Host headers are required"
    #     }, 401
    
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
        valid_domains = [
            'youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com',
            'music.youtube.com', 'gaming.youtube.com'
        ]
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
        raise ValidationError(
            f"Video duration ({format_duration(duration)}) exceeds maximum "
            f"allowed duration ({format_duration(MAX_VIDEO_DURATION)})"
        )
    
    if start is None or end is None:
        return
    
    if not isinstance(start, int) or not isinstance(end, int):
        raise ValidationError("Start and end times must be integers")
    
    if start < 0 or end < 0:
        raise ValidationError("Start and end times must be non-negative")
    
    if start >= end:
        raise ValidationError("Start time must be less than end time")
    
    if end > duration:
        raise ValidationError(
            f"End time ({format_duration(end)}) exceeds video duration "
            f"({format_duration(duration)})"
        )
    
    clip_duration = end - start
    if clip_duration < MIN_CLIP_DURATION:
        raise ValidationError(
            f"Clip duration must be at least {MIN_CLIP_DURATION} second(s)"
        )
    
    if clip_duration > MAX_CLIP_DURATION:
        raise ValidationError(
            f"Clip duration ({format_duration(clip_duration)}) cannot exceed "
            f"maximum allowed ({format_duration(MAX_CLIP_DURATION)})"
        )


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
            'extract_flat': False,
            'cookiefile': None,  # Don't use cookies by default
            'no_check_certificate': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Extract available formats
            formats = info.get('formats', [])
            available_qualities = set()
            
            for fmt in formats:
                height = fmt.get('height')
                if height:
                    if height >= 2160:
                        available_qualities.add('2160p')
                    elif height >= 1440:
                        available_qualities.add('1440p')
                    elif height >= 1080:
                        available_qualities.add('1080p')
                    elif height >= 720:
                        available_qualities.add('720p')
                    elif height >= 480:
                        available_qualities.add('480p')
                    elif height >= 360:
                        available_qualities.add('360p')
            
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'upload_date': info.get('upload_date'),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'description': info.get('description', ''),
                'thumbnail': info.get('thumbnail'),
                'webpage_url': info.get('webpage_url', url),
                'available_qualities': sorted(list(available_qualities), 
                                            key=lambda x: int(x[:-1]), reverse=True),
                'formats_count': len(formats),
                'has_subtitles': bool(info.get('subtitles')),
                'subtitle_languages': list(info.get('subtitles', {}).keys()),
                'chapters': info.get('chapters', []),
                'tags': info.get('tags', [])
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


def get_format_selector(options: DownloadOptions) -> str:
    """
    Get yt-dlp format selector based on options.
    
    Args:
        options: Download options
        
    Returns:
        Format selector string for yt-dlp
    """
    if options.custom_format:
        return options.custom_format
    
    if options.download_mode == DownloadMode.AUDIO_ONLY:
        if options.audio_quality == AudioQuality.BEST:
            return "bestaudio/best"
        elif options.audio_quality == AudioQuality.WORST:
            return "worstaudio/worst"
        else:
            abr = options.audio_quality.value
            return f"bestaudio[abr<={abr}]/bestaudio/best"
    
    # Video + Audio formats
    video_selector = ""
    audio_selector = "bestaudio"
    
    # Configure video quality
    if options.video_quality == VideoQuality.BEST:
        video_selector = "bestvideo"
    elif options.video_quality == VideoQuality.WORST:
        video_selector = "worstvideo"
    else:
        height = options.video_quality.value[:-1]  # Remove 'p'
        video_selector = f"bestvideo[height<={height}]"
    
    # Configure audio quality
    if options.audio_quality != AudioQuality.BEST:
        if options.audio_quality == AudioQuality.WORST:
            audio_selector = "worstaudio"
        else:
            abr = options.audio_quality.value
            audio_selector = f"bestaudio[abr<={abr}]"
    
    # Prefer mp4 container
    format_string = f"{video_selector}[ext=mp4]+{audio_selector}[ext=m4a]/{video_selector}+{audio_selector}/best"
    
    return format_string


def get_download_options_from_request(data: Dict[str, Any]) -> DownloadOptions:
    """
    Parse request data into DownloadOptions object.
    
    Args:
        data: Request JSON data
        
    Returns:
        DownloadOptions object
        
    Raises:
        ValidationError: If validation fails
    """
    url = data.get("url")
    if not url:
        raise ValidationError("URL is required")
    
    if not validate_youtube_url(url):
        raise ValidationError("Invalid YouTube URL")
    
    # Parse quality options
    video_quality_str = data.get("video_quality", "best").lower()
    try:
        video_quality = VideoQuality(video_quality_str)
    except ValueError:
        valid_qualities = [q.value for q in VideoQuality]
        raise ValidationError(f"Invalid video quality. Valid options: {valid_qualities}")
    
    audio_quality_str = data.get("audio_quality", "best").lower()
    try:
        audio_quality = AudioQuality(audio_quality_str)
    except ValueError:
        valid_qualities = [q.value for q in AudioQuality]
        raise ValidationError(f"Invalid audio quality. Valid options: {valid_qualities}")
    
    # Parse download mode
    download_mode_str = data.get("download_mode", "balanced").lower()
    try:
        download_mode = DownloadMode(download_mode_str)
    except ValueError:
        valid_modes = [m.value for m in DownloadMode]
        raise ValidationError(f"Invalid download mode. Valid options: {valid_modes}")
    
    # Parse subtitle languages
    subtitle_languages = data.get("subtitle_languages", [])
    if isinstance(subtitle_languages, str):
        subtitle_languages = [lang.strip() for lang in subtitle_languages.split(",")]
    
    return DownloadOptions(
        url=url,
        start_time=data.get("start"),
        end_time=data.get("end"),
        video_quality=video_quality,
        audio_quality=audio_quality,
        download_mode=download_mode,
        extract_audio=data.get("extract_audio", False),
        include_subtitles=data.get("include_subtitles", False),
        subtitle_languages=subtitle_languages,
        thumbnail=data.get("thumbnail", False),
        metadata=data.get("metadata", True),
        custom_format=data.get("custom_format")
    )


def download_video(options: DownloadOptions) -> str:
    """
    Download video from YouTube with customizable options.
    
    Args:
        options: Download configuration options
        
    Returns:
        Path to downloaded file
        
    Raises:
        VideoDownloadError: If download fails
    """
    try:
        # Get video info first
        info = extract_video_info(options.url)
        video_title = sanitize_filename(info['title'])
        
        # Validate clip times if specified
        validate_clip_times(options.start_time, options.end_time, info['duration'])
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # For audio extraction, don't add extension yet - yt-dlp will handle it
        if options.extract_audio:
            filename = f"{video_title}_{timestamp}"
            file_path = os.path.join(DOWNLOAD_FOLDER, filename)
        else:
            filename = f"{video_title}_{timestamp}.mp4"
            file_path = os.path.join(DOWNLOAD_FOLDER, filename)
        
        # Configure download options
        format_selector = get_format_selector(options)
        
        ydl_opts = {
            'format': format_selector,
            'outtmpl': file_path,
            'quiet': True,
            'no_warnings': True,
            'writesubtitles': options.include_subtitles,
            'writeautomaticsub': False,
            'writeinfojson': options.metadata,
            'writethumbnail': options.thumbnail,
            'embed_subs': False,  # Keep subtitles as separate files
            'keepvideo': False,
        }
        
        # Configure output format
        if not options.extract_audio:
            ydl_opts['merge_output_format'] = 'mp4'
        
        # Configure subtitle languages
        if options.include_subtitles and options.subtitle_languages:
            ydl_opts['subtitleslangs'] = options.subtitle_languages
        elif options.include_subtitles:
            ydl_opts['subtitleslangs'] = ['en']  # Default to English
        
        # Configure post-processors - FIXED FOR AUDIO CLIPS
        postprocessors = []
        
        # Handle audio extraction and clipping together
        if options.extract_audio:
            if options.start_time is not None and options.end_time is not None:
                # For audio clips, do everything in one FFmpeg command
                clip_duration = options.end_time - options.start_time
                quality = options.audio_quality.value if options.audio_quality != AudioQuality.BEST else '192'
                
                # Single post-processor that clips AND extracts audio
                audio_clip_postprocessor = {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': quality,
                    'when': 'post_process',
                }
                
                # Add clipping arguments to the audio extraction
                ydl_opts['postprocessor_args'] = {
                    'ffmpeg': [
                        '-ss', str(options.start_time),
                        '-t', str(clip_duration),
                        '-avoid_negative_ts', 'make_zero'
                    ]
                }
                
                postprocessors.append(audio_clip_postprocessor)
                
                logger.info(f"Audio clip: extracting {format_duration(clip_duration)} from {format_duration(options.start_time)} to {format_duration(options.end_time)}")
            else:
                # Just audio extraction, no clipping
                audio_postprocessor = {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': options.audio_quality.value if options.audio_quality != AudioQuality.BEST else '192',
                }
                postprocessors.append(audio_postprocessor)
                
        else:
            # Video-only clipping (existing logic)
            if options.start_time is not None and options.end_time is not None:
                clip_duration = options.end_time - options.start_time
                
                if options.download_mode == DownloadMode.FAST:
                    ffmpeg_args = [
                        '-ss', str(options.start_time),
                        '-t', str(clip_duration),
                        '-c:v', 'copy',
                        '-c:a', 'copy',
                        '-copyts',
                        '-avoid_negative_ts', 'make_zero',
                        '-fflags', '+genpts'
                    ]
                    logger.info(f"Fast clipping from {format_duration(options.start_time)} "
                               f"to {format_duration(options.end_time)} (stream copy mode)")
                elif options.download_mode == DownloadMode.PRECISE:
                    ffmpeg_args = [
                        '-ss', str(options.start_time),
                        '-t', str(clip_duration),
                        '-c:v', 'libx264',
                        '-preset', 'fast',
                        '-crf', '23',
                        '-c:a', 'aac',
                        '-b:a', '192k',
                        '-avoid_negative_ts', 'make_zero'
                    ]
                    logger.info(f"Precise clipping from {format_duration(options.start_time)} "
                               f"to {format_duration(options.end_time)} (re-encoding mode)")
                else:  # BALANCED
                    ffmpeg_args = [
                        '-ss', str(options.start_time),
                        '-t', str(clip_duration),
                        '-c:v', 'libx264',
                        '-preset', 'veryfast',
                        '-crf', '25',
                        '-c:a', 'copy',
                        '-avoid_negative_ts', 'make_zero'
                    ]
                    logger.info(f"Balanced clipping from {format_duration(options.start_time)} "
                               f"to {format_duration(options.end_time)} (fast encode mode)")
                
                video_postprocessor = {
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }
                
                ydl_opts['postprocessor_args'] = {'ffmpeg': ffmpeg_args}
                postprocessors.append(video_postprocessor)
        
        if postprocessors:
            ydl_opts['postprocessors'] = postprocessors
        
        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([options.url])
        
        # For audio extraction, find the actual created file (yt-dlp adds .mp3)
        if options.extract_audio:
            # Look for the created audio file
            for f in os.listdir(DOWNLOAD_FOLDER):
                if f.startswith(filename) and f.endswith('.mp3'):
                    file_path = os.path.join(DOWNLOAD_FOLDER, f)
                    break
        
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
        "service": "Enhanced YouTube Video Clipper API",
        "version": "2.0.0",
        "description": "Advanced YouTube video downloader with customizable quality, clipping, and processing options",
        "yt_dlp_version": "2025.08.20",
        "endpoints": {
            "/download": "POST - Download video with advanced options",
            "/info": "POST - Get detailed video information",
            "/health": "GET - Health check",
            "/formats": "POST - Get available formats for a video"
        },
        "parameters": {
            "url": "YouTube video URL (required)",
            "start": "Start time in seconds for clipping (optional)",
            "end": "End time in seconds for clipping (optional)",
            "video_quality": f"Video quality: {[q.value for q in VideoQuality]} (default: best)",
            "audio_quality": f"Audio quality: {[q.value for q in AudioQuality]} (default: best)",
            "download_mode": f"Download mode: {[m.value for m in DownloadMode]} (default: balanced)",
            "extract_audio": "Extract audio only (boolean, default: false)",
            "include_subtitles": "Include subtitles (boolean, default: false)",
            "subtitle_languages": "Subtitle languages (array/comma-separated, e.g., ['en', 'es'])",
            "thumbnail": "Download thumbnail (boolean, default: false)",
            "metadata": "Include metadata (boolean, default: true)",
            "custom_format": "Custom yt-dlp format selector (overrides quality settings)"
        },
        "download_modes": {
            "fast": "Stream copying - fastest but may have sync issues",
            "balanced": "Fast encode - good balance of speed and quality",
            "precise": "Full re-encode - slowest but most reliable",
            "audio_only": "Audio extraction only"
        },
        "limits": {
            "max_clip_duration": f"{format_duration(MAX_CLIP_DURATION)}",
            "min_clip_duration": f"{MIN_CLIP_DURATION} second",
            "max_video_duration": f"{format_duration(MAX_VIDEO_DURATION)}",
            "max_file_age": f"{MAX_FILE_AGE_HOURS} hour(s)",
            "supported_domains": ["youtube.com", "youtu.be", "music.youtube.com"]
        }
    })


@app.route("/download", methods=["POST"])
def download_video_endpoint():
    """Enhanced download video endpoint with advanced options."""
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
        
        # Parse and validate options
        try:
            options = get_download_options_from_request(data)
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        
        # Download video
        file_path = download_video(options)
        filename = os.path.basename(file_path)
        
        # If subtitles were requested, create a ZIP with video + subtitle files
        if options.include_subtitles:
            # Get the base filename (without extension)
            base_name = os.path.splitext(filename)[0]
            
            # Find all subtitle files
            subtitle_files = []
            for f in os.listdir(DOWNLOAD_FOLDER):
                if f.startswith(base_name) and ('.vtt' in f or '.srt' in f or '.ass' in f):
                    subtitle_files.append(f)
            
            if subtitle_files:
                # Create ZIP file
                zip_filename = f"{base_name}_with_subs.zip"
                zip_path = os.path.join(DOWNLOAD_FOLDER, zip_filename)
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add main video file
                    zipf.write(file_path, filename)
                    
                    # Add subtitle files
                    for sub_file in subtitle_files:
                        sub_path = os.path.join(DOWNLOAD_FOLDER, sub_file)
                        if os.path.exists(sub_path):
                            zipf.write(sub_path, sub_file)
                
                logger.info(f"Created ZIP with video + {len(subtitle_files)} subtitle files")
                
                return send_file(
                    zip_path,
                    as_attachment=True,
                    download_name=zip_filename,
                    mimetype='application/zip'
                )
        
        # If no subtitles requested or no subtitle files found, send just the video/audio
        mime_type = 'audio/mpeg' if options.extract_audio else 'video/mp4'
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype=mime_type
        )
        
    except VideoDownloadError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500


@app.route("/info", methods=["POST"])
def get_video_info_endpoint():
    """Get detailed video information endpoint."""
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
            "like_count": info['like_count'],
            "description": info['description'][:500] + "..." if len(info['description']) > 500 else info['description'],
            "thumbnail": info['thumbnail'],
            "webpage_url": info['webpage_url'],
            "available_qualities": info['available_qualities'],
            "formats_count": info['formats_count'],
            "has_subtitles": info['has_subtitles'],
            "subtitle_languages": info['subtitle_languages'],
            "chapters": info['chapters'],
            "tags": info['tags'][:10]  # Limit to first 10 tags
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


@app.route("/formats", methods=["POST"])
def get_video_formats_endpoint():
    """Get available formats for a video."""
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
        
        # Get detailed format information
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'listformats': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            formats = []
            for fmt in info.get('formats', []):
                format_info = {
                    'format_id': fmt.get('format_id'),
                    'ext': fmt.get('ext'),
                    'resolution': fmt.get('resolution', 'unknown'),
                    'fps': fmt.get('fps'),
                    'vcodec': fmt.get('vcodec'),
                    'acodec': fmt.get('acodec'),
                    'filesize': fmt.get('filesize'),
                    'tbr': fmt.get('tbr'),  # Total bitrate
                    'vbr': fmt.get('vbr'),  # Video bitrate
                    'abr': fmt.get('abr'),  # Audio bitrate
                    'width': fmt.get('width'),
                    'height': fmt.get('height'),
                    'format_note': fmt.get('format_note', ''),
                    'quality': fmt.get('quality'),
                }
                formats.append(format_info)
        
        return jsonify({
            "status": "success",
            "formats": formats,
            "total_formats": len(formats)
        })
        
    except Exception as e:
        logger.error(f"Error getting formats: {e}")
        return jsonify({"error": "Failed to get video formats"}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "Enhanced YouTube Clipper API",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "yt_dlp_version": "2025.08.20",
        "python_version": "3.10+",
        "download_folder": DOWNLOAD_FOLDER,
        "available_space": "dynamic cleanup"
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
    # For production on Windows, use waitress instead of gunicorn
    # For development/testing only
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False, threaded=True)


