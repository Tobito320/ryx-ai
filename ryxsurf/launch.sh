#!/bin/bash
cd /home/tobi/ryx-ai/ryxsurf
source /home/tobi/ryx-ai/venv/bin/activate
exec python main.py "$@"
