@echo off
pip install -r requirements.txt
python scripts\fetch_news.py
python -m http.server 8000
