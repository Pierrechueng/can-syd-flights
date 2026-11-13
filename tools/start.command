#!/bin/bash
cd "$(dirname "$0")"
PY=/Users/pierre/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3
[ -x "$PY" ] || PY=python3
pkill -f "server.py" 2>/dev/null
nohup "$PY" server.py >> server.log 2>&1 &
sleep 2
open http://127.0.0.1:8791/
