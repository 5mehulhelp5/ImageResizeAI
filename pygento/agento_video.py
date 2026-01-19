#!/usr/bin/env python3
"""
Genaker ImageAIBundle - Python Console Command
Generate video from image using Google Gemini Veo 3.1 API

This script provides a Python implementation of the agento:video console command.
It uses Google's Generative AI SDK and handles 302 redirects properly when downloading videos.

Configuration:
    - Environment variables (from .env file or system env):
        - GEMINI_API_KEY: Google Gemini API key
        - MAGENTO_BASE_PATH: Base path for Magento installation
        - VIDEO_SAVE_PATH: Path where videos should be saved (relative to base_path or absolute)
        - MAGENTO_BASE_URL: Base URL for generating full video URLs
    - Command line arguments override environment variables
"""

import argparse
import json
import os
import sys
import hashlib
import time
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import requests
from google import generativeai as genai

# Try to load python-dotenv if available, otherwise use manual .env parsing
try:
    from dotenv import load_dotenv
    _dotenv_available = True
except ImportError:
    _dotenv_available = False


def load_env_file(env_path: Optional[str] = None) -> None:
    """
    Load environment variables from .env file
    
    Args:
        env_path: Path to .env file (defaults to .env in current directory or script directory)
    """
    if _dotenv_available:
        # Use python-dotenv if available
        if env_path:
            load_dotenv(env_path)
        else:
            # Try script directory first, then current directory
            script_dir = Path(__file__).parent.parent
            env_file = script_dir / '.env'
            if not env_file.exists():
                env_file = Path.cwd() / '.env'
            if env_file.exists():
                load_dotenv(env_file)
            else:
                load_dotenv()  # Try default locations
    else:
        # Manual .env parsing (basic support)
        if env_path:
            env_file = Path(env_path)
        else:
            script_dir = Path(__file__).parent.parent
            env_file = script_dir / '.env'
            if not env_file.exists():
                env_file = Path.cwd() / '.env'
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        # Only set if not already in environment
                        if key and key not in os.environ:
                            os.environ[key] = value


class GeminiVideoService:
    """Core service for interacting with Google Gemini Veo 3.1 API"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, verbose: bool = False):
        """
        Initialize the video service
        
        Args:
            api_key: Google Gemini API key (if not provided, will be read from GEMINI_API_KEY environment variable)
            base_url: Base URL for API (if not provided, will be read from GOOGLE_API_DOMAIN env var or default to production)
            verbose: Enable verbose debug output
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY') or ''
        
        # Get base URL from parameter, env var, or default to production
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            env_base_url = os.getenv('GOOGLE_API_DOMAIN')
            if env_base_url:
                self.base_url = env_base_url.rstrip('/')
            else:
                # Default to production API
                self.base_url = 'https://generativelanguage.googleapis.com/v1beta'
        
        self.model_name = 'veo-3.1-generate-preview'
        self.verbose = verbose
    
    def is_available(self) -> bool:
        """Check if the service is available"""
        return bool(self.api_key)
    
    def submit_video_generation_request(
        self,
        prompt: str,
        image_data: bytes,
        mime_type: str,
        aspect_ratio: str = '16:9',
        second_image_data: Optional[bytes] = None,
        second_mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit video generation request to Veo API
        
        Args:
            prompt: Video generation prompt
            image_data: First image data as bytes
            mime_type: MIME type of first image
            aspect_ratio: Aspect ratio (e.g., "16:9", "9:16", "1:1")
            second_image_data: Optional second image data as bytes
            second_mime_type: Optional MIME type of second image
            
        Returns:
            API response with operation name
            
        Raises:
            RuntimeError: If API request fails
        """
        if not self.is_available():
            raise RuntimeError(
                'Gemini video service is not available. Please configure the Gemini API key.'
            )
        
        import base64
        
        endpoint = f"{self.base_url}/models/{self.model_name}:predictLongRunning"
        
        # Prepare payload with first image
        instance_data = {
            'prompt': prompt,
            'image': {
                'bytesBase64Encoded': base64.b64encode(image_data).decode('utf-8'),
                'mimeType': mime_type
            }
        }
        
        # Add second image if provided
        if second_image_data and second_mime_type:
            instance_data['image2'] = {
                'bytesBase64Encoded': base64.b64encode(second_image_data).decode('utf-8'),
                'mimeType': second_mime_type
            }
        
        # Prepare payload
        payload = {
            'instances': [instance_data],
            'parameters': {}
        }
        
        # Add aspect ratio if specified
        if aspect_ratio:
            payload['parameters']['aspectRatio'] = aspect_ratio
        
        # Debug output
        if self.verbose:
            print("=" * 80, file=sys.stderr)
            print("DEBUG: Video Generation Request", file=sys.stderr)
            print("=" * 80, file=sys.stderr)
            print(f"Endpoint: {endpoint}", file=sys.stderr)
            print(f"Model: {self.model_name}", file=sys.stderr)
            print(f"Prompt: {prompt}", file=sys.stderr)
            print(f"Image 1 - Size: {len(image_data)} bytes, MIME: {mime_type}", file=sys.stderr)
            if second_image_data:
                print(f"Image 2 - Size: {len(second_image_data)} bytes, MIME: {second_mime_type}", file=sys.stderr)
            print(f"Aspect Ratio: {aspect_ratio}", file=sys.stderr)
            print("\nRequest Payload:", file=sys.stderr)
            # Create a copy of payload for display (truncate base64 data)
            debug_payload = json.loads(json.dumps(payload))
            if 'instances' in debug_payload and len(debug_payload['instances']) > 0:
                instance = debug_payload['instances'][0]
                if 'image' in instance:
                    img_data = instance['image']['bytesBase64Encoded']
                    instance['image']['bytesBase64Encoded'] = f"{img_data[:50]}... (truncated, {len(img_data)} chars total)"
                if 'image2' in instance:
                    img2_data = instance['image2']['bytesBase64Encoded']
                    instance['image2']['bytesBase64Encoded'] = f"{img2_data[:50]}... (truncated, {len(img2_data)} chars total)"
            print(json.dumps(debug_payload, indent=2), file=sys.stderr)
            print("=" * 80, file=sys.stderr)
        
        # Make API request
        headers = {
            'x-goog-api-key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(endpoint, json=payload, headers=headers, timeout=60)
            
            if self.verbose:
                print("\n[API Response] Status Code:", response.status_code, file=sys.stderr)
                print("[API Response] Headers:", dict(response.headers), file=sys.stderr)
                try:
                    response_data = response.json()
                    print("[API Response] Body:", file=sys.stderr)
                    print(json.dumps(response_data, indent=2), file=sys.stderr)
                except:
                    print("[API Response] Body (raw):", response.text[:500], file=sys.stderr)
                print("=" * 80, file=sys.stderr)
            
            response.raise_for_status()
            
            data = response.json()
            
            if 'name' not in data:
                raise RuntimeError('Invalid API response: operation name not found')
            
            return {
                'operationName': data['name'],
                'done': data.get('done', False),
                'status': 'completed' if data.get('done', False) else 'running'
            }
            
        except requests.RequestException as e:
            if self.verbose:
                print(f"\n[API Error] Request Exception: {str(e)}", file=sys.stderr)
                if hasattr(e, 'response') and e.response is not None:
                    print(f"[API Error] Response Status: {e.response.status_code}", file=sys.stderr)
                    try:
                        print(f"[API Error] Response Body: {json.dumps(e.response.json(), indent=2)}", file=sys.stderr)
                    except:
                        print(f"[API Error] Response Body (raw): {e.response.text[:500]}", file=sys.stderr)
            raise RuntimeError(f'Gemini API request failed: {str(e)}')
        except Exception as e:
            if self.verbose:
                print(f"\n[API Error] Exception: {str(e)}", file=sys.stderr)
            raise RuntimeError(f'Video generation failed: {str(e)}')
    
    def poll_operation_status(self, operation_name: str, max_wait_seconds: int = 300, poll_interval_seconds: int = 10) -> Dict[str, Any]:
        """
        Poll operation status until completion
        
        Args:
            operation_name: Operation name/ID
            max_wait_seconds: Maximum time to wait in seconds
            poll_interval_seconds: Interval between polls in seconds
            
        Returns:
            Operation response data
            
        Raises:
            RuntimeError: If polling fails or times out
        """
        if not self.is_available():
            raise RuntimeError('Gemini video service is not available.')
        
        poll_url = f"{self.base_url}/{operation_name}"
        headers = {
            'x-goog-api-key': self.api_key
        }
        
        start_time = time.time()
        spinner_frames = [
            "🎬 Generating video",
            "🎥 Creating magic",
            "✨ Crafting frames",
            "🎞️  Processing scenes",
            "🎭 Building story",
            "🎨 Adding effects",
            "🌟 Finalizing"
        ]
        spinner_idx = 0
        last_spinner_time = start_time
        
        # Show initial message
        if not self.verbose:
            print("🎬 Starting video generation...", file=sys.stderr, end='', flush=True)
        
        while True:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > max_wait_seconds:
                if not self.verbose:
                    print("\n", file=sys.stderr, end='')
                raise RuntimeError(f'Video generation timeout after {max_wait_seconds} seconds')
            
            # Update spinner animation (every 0.8 seconds, only if not verbose)
            if not self.verbose:
                current_time = time.time()
                if current_time - last_spinner_time >= 0.8:
                    spinner_msg = spinner_frames[spinner_idx % len(spinner_frames)]
                    elapsed_str = f" ({int(elapsed)}s)"
                    print(f"\r{spinner_msg}{elapsed_str}", file=sys.stderr, end='', flush=True)
                    spinner_idx += 1
                    last_spinner_time = current_time
            
            # Poll operation status
            try:
                response = requests.get(poll_url, headers=headers, timeout=poll_interval_seconds + 5)
                
                # Debug output for polling
                if self.verbose:
                    print(f"\n[Poll {int(elapsed)}s] Status Code: {response.status_code}", file=sys.stderr)
                    if response.status_code == 200:
                        try:
                            poll_data = response.json()
                            # Real Gemini API doesn't return progress percentage
                            print(f"  Elapsed: {int(elapsed)}s", file=sys.stderr)
                            print(f"  Done: {poll_data.get('done', False)}", file=sys.stderr)
                            print(f"\n[Poll {int(elapsed)}s] Raw API Response:", file=sys.stderr)
                            print(json.dumps(poll_data, indent=2), file=sys.stderr)
                        except Exception as e:
                            print(f"  Error parsing response: {str(e)}", file=sys.stderr)
                            print(f"  Raw response: {response.text[:500]}", file=sys.stderr)
                
                response.raise_for_status()
                
                data = response.json()
                
                # Check if operation is done
                if data.get('done', False):
                    if not self.verbose:
                        print("\r✅ Video generation complete!" + " " * 20, file=sys.stderr)
                    if self.verbose:
                        print("\n[Poll Complete] Final Response:", file=sys.stderr)
                        print(json.dumps(data, indent=2), file=sys.stderr)
                    return data
                
                # Not done yet, wait and poll again
                # During sleep, continue showing spinner animation if not verbose
                if not self.verbose:
                    sleep_interval = 0.5  # Update spinner every 0.5 seconds
                    slept = 0
                    while slept < poll_interval_seconds:
                        time.sleep(sleep_interval)
                        slept += sleep_interval
                        elapsed = time.time() - start_time
                        current_time = time.time()
                        if current_time - last_spinner_time >= 0.8:
                            spinner_msg = spinner_frames[spinner_idx % len(spinner_frames)]
                            elapsed_str = f" ({int(elapsed)}s)"
                            print(f"\r{spinner_msg}{elapsed_str}", file=sys.stderr, end='', flush=True)
                            spinner_idx += 1
                            last_spinner_time = current_time
                else:
                    time.sleep(poll_interval_seconds)
                
            except requests.RequestException as e:
                if self.verbose:
                    print(f"\n[Poll Error] Request Exception: {str(e)}", file=sys.stderr)
                    if hasattr(e, 'response') and e.response is not None:
                        print(f"[Poll Error] Response Status: {e.response.status_code}", file=sys.stderr)
                        try:
                            print(f"[Poll Error] Response Body: {json.dumps(e.response.json(), indent=2)}", file=sys.stderr)
                        except:
                            print(f"[Poll Error] Response Body (raw): {e.response.text[:500]}", file=sys.stderr)
                raise RuntimeError(f'Video operation polling failed: {str(e)}')
    
    def extract_video_uri(self, operation_data: Dict[str, Any]) -> str:
        """
        Extract video URI from completed operation response
        
        Args:
            operation_data: Completed operation response data
            
        Returns:
            Video URI string
            
        Raises:
            RuntimeError: If video URI not found or operation was filtered
        """
        # Check for safety filter blocks
        if 'response' in operation_data:
            response_data = operation_data['response']
            if 'generateVideoResponse' in response_data:
                gen_res = response_data['generateVideoResponse']
                
                # Catch Safety Filter Blocks (RAI Media Filtered)
                if 'raiMediaFilteredReasons' in gen_res:
                    reasons = gen_res['raiMediaFilteredReasons']
                    reasons_str = ", ".join(reasons) if isinstance(reasons, list) else str(reasons)
                    filtered_count = gen_res.get('raiMediaFilteredCount', len(reasons) if isinstance(reasons, list) else 1)
                    raise RuntimeError(
                        f"Video generation was blocked by safety filters. "
                        f"Reason(s): {reasons_str}. "
                        f"Filtered count: {filtered_count}. "
                        f"Suggestions: 1) Simplify your prompt (remove brand names, celebrities, or copyrighted content), "
                        f"2) If audio is the issue, retry with --silent-video flag or add 'silent video' to your prompt, "
                        f"3) Check that your image doesn't contain restricted content. "
                        f"You have not been charged for this attempt."
                    )
                
                # Success Path - Extract video URI
                if 'generatedSamples' in gen_res and gen_res['generatedSamples']:
                    sample = gen_res['generatedSamples'][0]
                    if 'video' in sample and 'uri' in sample['video']:
                        return sample['video']['uri']
        
        raise RuntimeError('No video URI found in completed operation response')
    
    def download_video(self, video_uri: str) -> bytes:
        """
        Download video from URI with proper 302 redirect handling
        
        Args:
            video_uri: Video download URI
            
        Returns:
            Video content as bytes
            
        Raises:
            RuntimeError: If download fails
        """
        headers = {
            'x-goog-api-key': self.api_key
        }
        
        # Append API key to URI if it's a Google API URI and doesn't have it
        if 'generativelanguage.googleapis.com' in video_uri and 'key=' not in video_uri:
            separator = '&' if '?' in video_uri else '?'
            video_uri = f"{video_uri}{separator}key={self.api_key}"
        
        # Use requests with redirect following
        response = requests.get(
            video_uri,
            headers=headers,
            allow_redirects=True,
            timeout=300,  # 5 minutes for large video files
            stream=True
        )
        
        # Check for redirects (requests handles automatically, but log for debugging)
        if response.history:
            redirect_count = len(response.history)
            final_url = response.url
            print(f"Followed {redirect_count} redirect(s), final URL: {final_url}", file=sys.stderr)
        
        # Raise exception for non-2xx status codes
        response.raise_for_status()
        
        # Read content
        video_content = response.content
        
        if not video_content:
            raise RuntimeError("Video download returned empty content")
        
        return video_content


class GeminiVideoGenerator:
    """Generate videos using Google Gemini Veo 3.1 API"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_path: Optional[str] = None,
        base_url: Optional[str] = None,
        save_path: Optional[str] = None,
        verbose: bool = False
    ):
        """
        Initialize the video generator
        
        Args:
            api_key: Google Gemini API key (if not provided, will be read from GEMINI_API_KEY environment variable)
            base_path: Base path for Magento installation (defaults to current directory or MAGENTO_BASE_PATH env)
            base_url: Base URL for generating full video URLs (defaults to MAGENTO_BASE_URL env)
            save_path: Path where videos should be saved (relative to base_path or absolute, defaults to pub/media/video)
            verbose: Enable verbose debug output
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY') or ''
        
        # Resolve base_path: arg > env > current directory
        if base_path:
            self.base_path = Path(base_path).resolve()
        else:
            env_base_path = os.getenv('MAGENTO_BASE_PATH')
            if env_base_path:
                self.base_path = Path(env_base_path).resolve()
            else:
                self.base_path = Path.cwd()
        
        # Resolve save_path: arg > env > default (pub/media/video)
        if save_path:
            save_path_obj = Path(save_path)
            if save_path_obj.is_absolute():
                self.video_dir = save_path_obj
            else:
                # Relative to base_path
                self.video_dir = self.base_path / save_path
        else:
            env_save_path = os.getenv('VIDEO_SAVE_PATH')
            if env_save_path:
                save_path_obj = Path(env_save_path)
                if save_path_obj.is_absolute():
                    self.video_dir = save_path_obj
                else:
                    self.video_dir = self.base_path / env_save_path
            else:
                # Default: pub/media/video (matches PHP implementation)
                self.video_dir = self.base_path / 'pub' / 'media' / 'video'
        
        self.video_dir.mkdir(parents=True, exist_ok=True)
        
        # Get base URL for generating full video URLs
        # Base URL is optional - only needed for generating full video URLs in response
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            try:
                self.base_url = self._get_base_url()
            except RuntimeError:
                # Base URL is optional - use None if not available
                # Will use relative path in video URL if base_url is None
                self.base_url = None
        
        # Initialize video service (will get API key from env if not provided)
        # Pass None if empty string so service can try to get from env
        service_api_key = self.api_key if self.api_key else None
        self.verbose = verbose
        self.video_service = GeminiVideoService(api_key=service_api_key, verbose=self.verbose)
    
    def is_available(self) -> bool:
        """Check if the service is available"""
        return self.video_service.is_available()
    
    def _get_relative_video_path(self, filename: str) -> str:
        """
        Get relative path from base_path to video file for URL generation
        
        Args:
            filename: Video filename
            
        Returns:
            Relative path string (e.g., "media/video/filename.mp4")
        """
        video_file_path = self.video_dir / filename
        try:
            # Calculate relative path from base_path to video file
            relative_path = video_file_path.relative_to(self.base_path)
            # Convert to forward-slash path for URLs
            return str(relative_path).replace('\\', '/')
        except ValueError:
            # If video_dir is not under base_path, use absolute path or just filename
            # In this case, we'll use the filename only (less ideal but works)
            return filename
    
    def _get_base_url(self) -> str:
        """
        Get base URL for generating full video URLs
        
        Returns:
            Base URL (e.g., https://example.com)
            
        Raises:
            RuntimeError: If base URL cannot be determined
        """
        # Try environment variables
        base_url = os.getenv('MAGENTO_BASE_URL') or os.getenv('BASE_URL')
        if base_url:
            # Remove trailing slash and store code if present
            base_url = base_url.rstrip('/')
            # Remove store code (e.g., /default/)
            if '/default/' in base_url:
                base_url = base_url.replace('/default/', '/')
            return base_url.rstrip('/')
        
        # Try to detect from system environment variables
        # Check if we can determine from HTTP_HOST
        host = os.getenv('HTTP_HOST') or os.getenv('SERVER_NAME')
        if host:
            # Use HTTPS if available, otherwise HTTP
            scheme = 'https' if os.getenv('HTTPS') == 'on' else 'http'
            return f"{scheme}://{host}"
        
        # Return None if base URL cannot be determined
        # This allows the script to work with external URLs without requiring base URL
        return None
    
    def is_url(self, path_or_url: str) -> bool:
        """
        Check if the input is a URL
        
        Args:
            path_or_url: Path or URL string
            
        Returns:
            True if URL, False otherwise
        """
        return path_or_url.startswith(('http://', 'https://'))
    
    def download_image_from_url(self, url: str) -> tuple[bytes, str]:
        """
        Download image from URL
        
        Args:
            url: Image URL
            
        Returns:
            Tuple of (image_data, mime_type)
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Determine MIME type from Content-Type header or URL
            mime_type = response.headers.get('Content-Type', '').split(';')[0].strip()
            if not mime_type or mime_type == 'application/octet-stream':
                mime_type, _ = mimetypes.guess_type(url)
                mime_type = mime_type or 'image/jpeg'
            
            return response.content, mime_type
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to download image from URL {url}: {str(e)}")
    
    def resolve_image_path(self, image_path: str) -> Optional[Path]:
        """
        Resolve image path (handle relative and absolute paths, or return None for URLs)
        
        Args:
            image_path: Image path (relative to pub/media/ or absolute) or URL
            
        Returns:
            Resolved absolute path, or None if URL
        """
        # If it's a URL, return None (will be handled separately)
        if self.is_url(image_path):
            return None
        
        image_path_obj = Path(image_path)
        
        # If absolute path, use as is
        if image_path_obj.is_absolute():
            return image_path_obj
        
        # If path starts with pub/media/, remove it
        if str(image_path).startswith('pub/media/'):
            image_path = str(image_path)[10:]
        
        # Resolve relative to pub/media/
        media_path = self.base_path / 'pub' / 'media' / image_path.lstrip('/')
        return media_path
    
    def generate_cache_key(self, image_path: str, prompt: str, aspect_ratio: str, second_image_path: Optional[str] = None) -> str:
        """
        Generate cache key from parameters
        
        Args:
            image_path: Path to image or URL
            prompt: Video generation prompt
            aspect_ratio: Aspect ratio
            second_image_path: Optional path to second image or URL
            
        Returns:
            Cache key string
        """
        def get_image_hash(path: str) -> str:
            """Helper to get hash of an image"""
            if self.is_url(path):
                image_data, _ = self.download_image_from_url(path)
                return hashlib.md5(image_data).hexdigest()
            else:
                image_path_obj = Path(path)
                if not image_path_obj.exists():
                    raise FileNotFoundError(f"Image not found: {path}")
                with open(image_path_obj, 'rb') as f:
                    return hashlib.md5(f.read()).hexdigest()
        
        # Get hash of first image
        image_hash = get_image_hash(image_path)
        
        # Get hash of second image if provided
        second_image_hash = ''
        if second_image_path:
            second_image_hash = get_image_hash(second_image_path)
        
        # Create cache key from all parameters
        cache_data = f"{image_hash}:{second_image_hash}:{prompt}:{aspect_ratio}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def get_cached_video(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Check if cached video exists
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached video info if exists, None otherwise
        """
        filename = f'veo_{cache_key}.mp4'
        video_path = self.video_dir / filename
        
        if video_path.exists():
            # Generate video URL
            relative_path = self._get_relative_video_path(filename)
            
            # If base_url is available, create full URL; otherwise use relative path
            if self.base_url:
                base_url_clean = self.base_url.rstrip('/')
                video_url = f"{base_url_clean}/{relative_path}"
            else:
                # No base URL available, use relative path
                video_url = f"/{relative_path}"
            
            return {
                'fromCache': True,
                'videoUrl': video_url,
                'videoPath': str(video_path),
                'status': 'completed'
            }
        
        return None
    
    def save_video(self, video_uri: str, cache_key: str) -> str:
        """
        Save video to local filesystem
        
        Args:
            video_uri: URI to download video from
            cache_key: Cache key for filename
            
        Returns:
            Path to saved video file
        """
        filename = f'veo_{cache_key}.mp4'
        video_path = self.video_dir / filename
        
        # Download video using service
        video_content = self.video_service.download_video(video_uri)
        
        # Save to file
        with open(video_path, 'wb') as f:
            f.write(video_content)
        
        return str(video_path)
    
    def _load_image(self, image_path: str) -> tuple[bytes, str, str]:
        """
        Load image data from path or URL
        
        Args:
            image_path: Path to image or URL
            
        Returns:
            Tuple of (image_data, mime_type, source_path_str)
        """
        if self.verbose:
            print(f"\n[Image Processing] Loading: {image_path}", file=sys.stderr)
        
        if self.is_url(image_path):
            # Download image from URL
            if self.verbose:
                print(f"  Type: External URL", file=sys.stderr)
            image_data, mime_type = self.download_image_from_url(image_path)
            source_path_str = image_path  # Keep URL for reference
            if self.verbose:
                print(f"  Downloaded: {len(image_data)} bytes", file=sys.stderr)
                print(f"  MIME Type: {mime_type}", file=sys.stderr)
        else:
            # Resolve image path
            source_path = self.resolve_image_path(image_path)
            if source_path is None or not source_path.exists():
                raise FileNotFoundError(f"Source image not found: {image_path}")
            
            if self.verbose:
                print(f"  Type: Local file", file=sys.stderr)
                print(f"  Resolved path: {source_path}", file=sys.stderr)
            
            # Read image file
            with open(source_path, 'rb') as f:
                image_data = f.read()
            
            if self.verbose:
                print(f"  File size: {len(image_data)} bytes", file=sys.stderr)
            
            # Determine MIME type using Python's mimetypes library (more robust)
            mime_type, _ = mimetypes.guess_type(str(source_path))
            mime_type = mime_type or 'image/jpeg'  # Default to JPEG if detection fails
            source_path_str = str(source_path)
            
            if self.verbose:
                print(f"  MIME Type: {mime_type}", file=sys.stderr)
        
        return image_data, mime_type, source_path_str
    
    def _get_image_reference_name(self, image_path: str) -> str:
        """
        Get a human-readable reference name for an image
        
        Args:
            image_path: Path to image or URL
            
        Returns:
            Reference name (e.g., "background.jpg", "summer_scene")
        """
        if self.is_url(image_path):
            # Extract filename from URL
            parsed = urlparse(image_path)
            filename = Path(parsed.path).stem or "image"
        else:
            # Get filename from path (with extension for clarity)
            path_obj = Path(image_path)
            filename = path_obj.stem or path_obj.name
        
        return filename
    
    def _enhance_prompt_with_image_references(
        self,
        prompt: str,
        image_path: str,
        second_image_path: Optional[str] = None,
        auto_reference: bool = True
    ) -> str:
        """
        Enhance prompt with image references to help AI understand which image to use for what
        
        Args:
            prompt: Original prompt
            image_path: Path to first image
            second_image_path: Optional path to second image
            auto_reference: If True, automatically add image context to prompt
            
        Returns:
            Enhanced prompt with image references
        """
        if not auto_reference or not second_image_path:
            return prompt
        
        # Get reference names for images
        image1_name = self._get_image_reference_name(image_path)
        image2_name = self._get_image_reference_name(second_image_path)
        
        # Check if prompt already contains image references
        prompt_lower = prompt.lower()
        has_reference = any(keyword in prompt_lower for keyword in [
            'image1', 'image2', 'first image', 'second image',
            'image 1', 'image 2', image1_name.lower(), image2_name.lower()
        ])
        
        # If prompt already references images, return as-is
        if has_reference:
            return prompt
        
        # Add image context to help AI understand which image is which
        # Format: "Using [image1] as the first image and [image2] as the second image: [original prompt]"
        # This helps the AI understand which image corresponds to which reference in the prompt
        enhanced_prompt = (
            f"Context: You have two images - '{image1_name}' (image1/first image) and "
            f"'{image2_name}' (image2/second image). {prompt.strip()}"
        )
        
        return enhanced_prompt
    
    def generate_video_from_image(
        self,
        image_path: str,
        prompt: str,
        aspect_ratio: str = '16:9',
        silent_video: bool = False,
        second_image_path: Optional[str] = None,
        auto_reference_images: bool = True
    ) -> Dict[str, Any]:
        """
        Generate video from image(s) using Gemini Veo 3.1 API
        
        Args:
            image_path: Path to source image or URL (http/https)
            prompt: Video generation prompt. You can reference images as:
                   - "image1" or "first image" for the first image
                   - "image2" or "second image" for the second image
                   - Use image filenames (e.g., "background.jpg", "foreground.png")
                   - Examples: "Use image1 as background", "Combine image2 with image1",
                              "Transition from first image to second image"
            aspect_ratio: Aspect ratio (e.g., "16:9", "9:16", "1:1")
            silent_video: If True, appends "silent video" to prompt
            second_image_path: Optional path to second image or URL (http/https)
            auto_reference_images: If True, automatically adds image context to prompt
                                  when second image is provided (default: True)
            
        Returns:
            Operation details or cached video details
        """
        if not self.is_available():
            raise RuntimeError(
                'Gemini video service is not available. Please configure the Gemini API key.'
            )
        
        # Load first image
        image_data, mime_type, source_path_str = self._load_image(image_path)
        
        # Load second image if provided
        second_image_data = None
        second_mime_type = None
        second_source_path_str = None
        if second_image_path:
            second_image_data, second_mime_type, second_source_path_str = self._load_image(second_image_path)
        
        # Enhance prompt with image references if second image is provided
        original_prompt = prompt
        final_prompt = self._enhance_prompt_with_image_references(
            prompt,
            image_path,
            second_image_path,
            auto_reference_images
        )
        
        if self.verbose:
            print(f"\n[Prompt Processing]", file=sys.stderr)
            print(f"Original Prompt: {original_prompt}", file=sys.stderr)
            if final_prompt != original_prompt:
                print(f"Enhanced Prompt: {final_prompt}", file=sys.stderr)
            else:
                print(f"Final Prompt: {final_prompt}", file=sys.stderr)
        
        # Append "silent video" to prompt if requested
        if silent_video:
            final_prompt = f"{final_prompt.strip()} silent video"
            if self.verbose:
                print(f"Added 'silent video': {final_prompt}", file=sys.stderr)
        
        # Generate cache key (include second image if provided)
        cache_key = self.generate_cache_key(
            source_path_str,
            final_prompt,
            aspect_ratio,
            second_source_path_str if second_image_path else None
        )
        
        # Check cache
        cached_video = self.get_cached_video(cache_key)
        if cached_video:
            return cached_video
        
        # Submit video generation request using service
        result = self.video_service.submit_video_generation_request(
            prompt=final_prompt,
            image_data=image_data,
            mime_type=mime_type,
            aspect_ratio=aspect_ratio,
            second_image_data=second_image_data,
            second_mime_type=second_mime_type
        )
        
        return {
            'operationName': result['operationName'],
            'cacheKey': cache_key,
            'done': result.get('done', False),
            'status': result.get('status', 'running')
        }
    
    def poll_video_operation(
        self,
        operation_name: str,
        max_wait_seconds: int = 300,
        poll_interval_seconds: int = 10,
        cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Poll operation status and get video when ready
        
        Args:
            operation_name: Operation name/ID
            max_wait_seconds: Maximum time to wait in seconds
            poll_interval_seconds: Interval between polls in seconds
            cache_key: Cache key for saving video
            
        Returns:
            Video details with URL and path
        """
        # Poll operation using service
        operation_data = self.video_service.poll_operation_status(
            operation_name,
            max_wait_seconds,
            poll_interval_seconds
        )
        
        # Extract video URI from response
        video_uri = self.video_service.extract_video_uri(operation_data)
        
        # Save video
        if cache_key:
            video_path = self.save_video(video_uri, cache_key)
        else:
            # Use operation name as cache key
            video_path = self.save_video(video_uri, operation_name.split('/')[-1])
        
        # Generate full video URL with domain (matches PHP implementation)
        video_filename = Path(video_path).name
        relative_path = self._get_relative_video_path(video_filename)
        
        # Use base URL if available, otherwise use relative path
        if self.base_url:
            # Ensure base_url doesn't have trailing slash
            base_url_clean = self.base_url.rstrip('/')
            video_url = f"{base_url_clean}/{relative_path}"
        else:
            # Use relative path if base URL not provided
            video_url = f"/{relative_path}"
        
        # Generate embed URL
        embed_url = f'<video controls width="100%" height="auto"><source src="{video_url}" type="video/mp4">Your browser does not support the video tag.</video>'
        
        return {
            'videoUrl': video_url,
            'videoPath': video_path,
            'embedUrl': embed_url,
            'status': 'completed'
        }


def main():
    """Main entry point for the console command"""
    # Load .env file first (before parsing arguments)
    load_env_file()
    
    parser = argparse.ArgumentParser(
        description='Generate video from image using Gemini Veo 3.1 API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables (from .env file or system env):
    GEMINI_API_KEY          Google Gemini API key
    MAGENTO_BASE_PATH       Base path for Magento installation
    VIDEO_SAVE_PATH         Path where videos should be saved (relative to base_path or absolute)
    MAGENTO_BASE_URL        Base URL for generating full video URLs

Command line arguments override environment variables.
        """
    )
    
    parser.add_argument(
        '-ip', '--image-path',
        required=True,
        nargs='+',
        help='Path(s) to source image(s) or URL(s) (relative to pub/media/, absolute path, or http/https URL). Can specify multiple paths/URLs.'
    )
    
    parser.add_argument(
        '-si', '--second-image',
        help='Optional second image path or URL to include in the payload for video generation (relative to pub/media/, absolute path, or http/https URL)'
    )
    
    parser.add_argument(
        '-p', '--prompt',
        required=True,
        help='Video generation prompt. When using --second-image, you can reference images as:\n'
             '  - "image1" or "first image" for the first image\n'
             '  - "image2" or "second image" for the second image\n'
             '  - Image filenames (e.g., "background.jpg", "foreground.png")\n'
             'Examples:\n'
             '  - "Use image1 as background and image2 as foreground"\n'
             '  - "Combine image2 with image1"\n'
             '  - "Transition from first image to second image"\n'
             '  - "Use background.jpg for the scene and foreground.png for the subject"'
    )
    
    parser.add_argument(
        '--no-auto-reference',
        action='store_true',
        help='Disable automatic image reference enhancement in prompt (use if you want full control over prompt)'
    )
    
    parser.add_argument(
        '-ar', '--aspect-ratio',
        default='16:9',
        help='Aspect ratio (e.g., "16:9", "9:16", "1:1"). Default: 16:9'
    )
    
    parser.add_argument(
        '-sv', '--silent-video',
        action='store_true',
        help='Generate silent video (helps avoid audio-related safety filters)'
    )
    
    parser.add_argument(
        '--sync',
        action='store_true',
        help='Wait for video generation to complete (synchronous mode)'
    )
    
    parser.add_argument(
        '--api-key',
        help='Google Gemini API key (overrides GEMINI_API_KEY environment variable)'
    )
    
    parser.add_argument(
        '--base-path',
        help='Base path for Magento installation (overrides MAGENTO_BASE_PATH environment variable)'
    )
    
    parser.add_argument(
        '--save-path',
        help='Path where videos should be saved, relative to base_path or absolute (overrides VIDEO_SAVE_PATH environment variable)'
    )
    
    parser.add_argument(
        '--base-url',
        help='Base URL for generating full video URLs (overrides MAGENTO_BASE_URL environment variable)'
    )
    
    parser.add_argument(
        '--env-file',
        help='Path to .env file (defaults to .env in script directory or current directory)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose debug output (shows image processing, prompt, and raw API request/response)'
    )
    
    args = parser.parse_args()
    
    # Load .env file if specified
    if args.env_file:
        load_env_file(args.env_file)
    
    # Get API key: arg > env
    api_key = args.api_key or os.getenv('GEMINI_API_KEY')
    if not api_key:
        result = {
            'success': False,
            'error': 'API key is required. Use --api-key or set GEMINI_API_KEY environment variable.'
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)
    
    try:
        # Initialize generator
        # Arguments override environment variables (handled in __init__)
        generator = GeminiVideoGenerator(
            api_key,
            base_path=args.base_path,
            base_url=args.base_url,
            save_path=args.save_path,
            verbose=args.verbose
        )
        
        # Check if service is available
        if not generator.is_available():
            result = {
                'success': False,
                'error': 'Video service is not available. Please configure Gemini API key.'
            }
            print(json.dumps(result, indent=2))
            sys.exit(1)
        
        # Process multiple image paths
        image_paths = args.image_path
        results = []
        errors = []
        
        for image_path in image_paths:
            try:
                # Generate video for this image (with optional second image)
                operation = generator.generate_video_from_image(
                    image_path,
                    args.prompt,
                    args.aspect_ratio,
                    args.silent_video,
                    args.second_image,  # Pass second image if provided
                    auto_reference_images=not args.no_auto_reference  # Enable auto-reference by default
                )
                
                # Check if video was returned from cache
                if operation.get('fromCache'):
                    result_item = {
                        'imagePath': image_path,
                        'success': True,
                        'status': 'completed',
                        'videoUrl': operation['videoUrl'],
                        'videoPath': operation['videoPath'],
                        'cached': True
                    }
                    if args.second_image:
                        result_item['secondImagePath'] = args.second_image
                    results.append(result_item)
                    continue
                
                # If sync option is set, wait for completion
                if args.sync:
                    result_data = generator.poll_video_operation(
                        operation['operationName'],
                        300,  # 5 minutes max wait
                        10,   # 10 seconds poll interval
                        operation.get('cacheKey')
                    )
                    
                    result_item = {
                        'imagePath': image_path,
                        'success': True,
                        'status': 'completed',
                        'videoUrl': result_data['videoUrl'],
                        'videoPath': result_data['videoPath'],
                        'embedUrl': result_data.get('embedUrl')
                    }
                    if args.second_image:
                        result_item['secondImagePath'] = args.second_image
                    results.append(result_item)
                else:
                    # Return operation ID for async mode
                    result_item = {
                        'imagePath': image_path,
                        'success': True,
                        'status': 'processing',
                        'operationName': operation['operationName'],
                        'message': 'Video generation started. Use --sync option to wait for completion.'
                    }
                    if args.second_image:
                        result_item['secondImagePath'] = args.second_image
                    results.append(result_item)
                    
            except FileNotFoundError as e:
                errors.append({
                    'imagePath': image_path,
                    'success': False,
                    'error': f'Source image not found: {str(e)}'
                })
            except Exception as e:
                errors.append({
                    'imagePath': image_path,
                    'success': False,
                    'error': str(e)
                })
        
        # Prepare final result
        if len(image_paths) == 1:
            # Single image - return single result format for backward compatibility
            if results:
                result = results[0]
            else:
                result = errors[0]
        else:
            # Multiple images - return array format
            result = {
                'success': len(errors) == 0,
                'total': len(image_paths),
                'succeeded': len(results),
                'failed': len(errors),
                'results': results,
                'errors': errors
            }
        
        print(json.dumps(result, indent=2))
        
        # Exit with error code if any failures
        if errors:
            sys.exit(1)
        sys.exit(0)
        
    except Exception as e:
        result = {
            'success': False,
            'error': str(e)
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
