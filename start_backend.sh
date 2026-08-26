#!/usr/bin/env bash
cd "$(dirname "$0")/python_backend"
uvicorn api_server:app --host 0.0.0.0 --port 8000
