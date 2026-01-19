#!/bin/bash
# Wrapper script to run agento_video.py without prompt interference
PS1='$ ' exec python3 "$(dirname "$0")/agento_video.py" "$@"
