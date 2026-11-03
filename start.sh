#!/bin/bash
set -e
# pyrofork and kurigram both install the "pyrogram" package; never let them coexist.
pip uninstall -y pyrofork pyrogram >/dev/null 2>&1 || true
pip install -r requirements.txt --no-cache-dir
python3 main.py
