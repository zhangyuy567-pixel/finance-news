#!/bin/bash
cd "$(dirname "$0")"
pip install -r requirements.txt
python3 scripts/fetch_news.py
python3 -m http.server 8000
