#!/usr/bin/env python3
"""
Video Generation API Server
HTTP API proxy for agento_video.py CLI command
Authenticates requests using API key from environment variable
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VideoAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for video generation API"""
    
    def __init__(self, *args, api_key=None, python_script=None, **kwargs):
        self.api_key = api_key
        self.python_script = python_script
        super().__init__(*args, **kwargs)
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Content-Length', '0')
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests for video generation"""
        try:
            # Check authentication
            if not self.authenticate():
                self.send_error(401, "Unauthorized: Invalid API key")
                return
            
            # Parse request
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "Bad Request: Empty request body")
                return
            
            body = self.rfile.read(content_length)
            try:
                request_data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError as e:
                self.send_error(400, f"Bad Request: Invalid JSON - {str(e)}")
                return
            
            # Validate required fields
            if 'image_path' not in request_data:
                self.send_error(400, "Bad Request: 'image_path' is required")
                return
            
            if 'prompt' not in request_data:
                self.send_error(400, "Bad Request: 'prompt' is required")
                return
            
            # Generate video
            result = self.generate_video(request_data)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result, indent=2).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}", exc_info=True)
            self.send_error(500, f"Internal Server Error: {str(e)}")
    
    def authenticate(self):
        """Authenticate request using API key"""
        # Get API key from Authorization header or X-API-Key header
        auth_header = self.headers.get('Authorization', '')
        api_key_header = self.headers.get('X-API-Key', '')
        
        # Extract key from "Bearer <key>" or direct key
        provided_key = None
        if auth_header.startswith('Bearer '):
            provided_key = auth_header[7:]
        elif auth_header:
            provided_key = auth_header
        elif api_key_header:
            provided_key = api_key_header
        
        # Compare with expected API key
        if not provided_key:
            return False
        
        return provided_key == self.api_key
    
    def generate_video(self, request_data):
        """Generate video by calling agento_video.py CLI"""
        try:
            # Build command
            python_executable = sys.executable
            command = [python_executable, str(self.python_script)]
            
            # Add image path(s) - support both single string and array
            image_paths = request_data['image_path']
            if isinstance(image_paths, str):
                image_paths = [image_paths]
            
            for image_path in image_paths:
                command.extend(['-ip', image_path])
            
            # Add second image if provided
            if 'second_image' in request_data and request_data['second_image']:
                command.extend(['-si', request_data['second_image']])
            
            # Add prompt
            command.extend(['-p', request_data['prompt']])
            
            # Add optional parameters
            if request_data.get('aspect_ratio'):
                command.extend(['-ar', request_data['aspect_ratio']])
            
            if request_data.get('silent_video', False):
                command.append('-sv')
            
            if request_data.get('sync', True):  # Default to sync mode for API
                command.append('--sync')
            
            if request_data.get('no_auto_reference', False):
                command.append('--no-auto-reference')
            
            # Add API key if provided in request (or use from env)
            api_key = request_data.get('api_key') or os.getenv('GEMINI_API_KEY')
            if api_key:
                command.extend(['--api-key', api_key])
            
            # Add base path if provided
            if request_data.get('base_path'):
                command.extend(['--base-path', request_data['base_path']])
            
            # Add save path if provided
            if request_data.get('save_path'):
                command.extend(['--save-path', request_data['save_path']])
            
            # Add base URL if provided
            if request_data.get('base_url'):
                command.extend(['--base-url', request_data['base_url']])
            
            # Add env file if provided
            if request_data.get('env_file'):
                command.extend(['--env-file', request_data['env_file']])
            
            logger.info(f"Executing command: {' '.join(command)}")
            
            # Execute command
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            # Parse output
            if result.returncode == 0:
                try:
                    # Try to parse JSON output
                    output_json = json.loads(result.stdout)
                    return {
                        'success': True,
                        'data': output_json
                    }
                except json.JSONDecodeError:
                    # If not JSON, return as text
                    return {
                        'success': True,
                        'data': {
                            'output': result.stdout,
                            'message': 'Video generation completed'
                        }
                    }
            else:
                # Error occurred
                error_msg = result.stderr or result.stdout or 'Unknown error'
                return {
                    'success': False,
                    'error': error_msg,
                    'return_code': result.returncode
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Video generation timed out after 10 minutes'
            }
        except Exception as e:
            logger.error(f"Error generating video: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def log_message(self, format, *args):
        """Override to use logger instead of stderr"""
        logger.info(f"{self.address_string()} - {format % args}")


def create_handler(api_key, python_script):
    """Factory function to create handler with dependencies"""
    def handler(*args, **kwargs):
        return VideoAPIHandler(*args, api_key=api_key, python_script=python_script, **kwargs)
    return handler


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Video Generation API Server')
    parser.add_argument(
        '--host',
        default=os.getenv('VIDEO_API_HOST', '127.0.0.1'),
        help='Host to bind to (default: 127.0.0.1 or VIDEO_API_HOST env)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv('VIDEO_API_PORT', '8080')),
        help='Port to bind to (default: 8080 or VIDEO_API_PORT env)'
    )
    parser.add_argument(
        '--api-key',
        default=os.getenv('VIDEO_API_KEY'),
        required=not bool(os.getenv('VIDEO_API_KEY')),
        help='API key for authentication (or set VIDEO_API_KEY env var)'
    )
    parser.add_argument(
        '--python-script',
        default=None,
        help='Path to agento_video.py script (auto-detected if not provided)'
    )
    
    args = parser.parse_args()
    
    # Auto-detect Python script path if not provided
    if not args.python_script:
        script_dir = Path(__file__).parent
        args.python_script = script_dir / 'agento_video.py'
        
        if not args.python_script.exists():
            logger.error(f"Python script not found: {args.python_script}")
            sys.exit(1)
    
    if not Path(args.python_script).exists():
        logger.error(f"Python script not found: {args.python_script}")
        sys.exit(1)
    
    # Create server
    handler = create_handler(args.api_key, Path(args.python_script))
    server = HTTPServer((args.host, args.port), handler)
    
    logger.info(f"Video API Server starting on http://{args.host}:{args.port}")
    logger.info(f"API Key: {'*' * (len(args.api_key) - 4) + args.api_key[-4:] if len(args.api_key) > 4 else '***'}")
    logger.info(f"Python Script: {args.python_script}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
        server.shutdown()


if __name__ == '__main__':
    main()
