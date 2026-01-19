#!/usr/bin/env python3
"""
Simple test script for Video API Server
"""

import requests
import json
import sys

def test_api_server(base_url="http://localhost:8080", api_key="test-key"):
    """Test the video API server"""
    
    url = f"{base_url}/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Test data with external URL
    data = {
        "image_path": "https://react-luma.cnxt.link/media/catalog/product/cache/decdbd3689b02cb033cfb093915217ec/w/t/wt09-white_main_1.jpg",
        "prompt": "Create a dynamic product showcase video",
        "sync": True,
        "aspect_ratio": "16:9"
    }
    
    print(f"Testing API server at {url}")
    print(f"Request data: {json.dumps(data, indent=2)}")
    print("-" * 50)
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=600)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("\n✓ Success!")
                if "data" in result and "videoUrl" in result["data"]:
                    print(f"Video URL: {result['data']['videoUrl']}")
            else:
                print(f"\n✗ Error: {result.get('error')}")
        else:
            print(f"\n✗ HTTP Error: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("✗ Error: Could not connect to server. Is it running?")
        print(f"  Start server with: python3 video_api_server.py --api-key {api_key}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Video API Server")
    parser.add_argument("--url", default="http://localhost:8080", help="API server URL")
    parser.add_argument("--api-key", default="test-key", help="API key")
    
    args = parser.parse_args()
    test_api_server(args.url, args.api_key)
