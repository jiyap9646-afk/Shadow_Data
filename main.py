import re
import os
import math
from datetime import datetime
from collections import Counter
from pathlib import Path

from flask import Flask, render_template, request, url_for
from bs4 import BeautifulSoup
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import pandas as pd   
import json  

app = Flask(__name__)

UPLOAD_FOLDER='uploads'
STATIC_FOLDER='static'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

from datetime import datetime


def parse_datetime(text: str):
    
    if not text:
        return None
    candidates = [
        "%B %d, %Y at %H:%M",
        "%B %d, %Y, %I:%M %p",
        "%b %d, %Y, %I:%M %p",
        "%Y-%m-%d %H:%M",
    ]
    for fmt in candidates:
        try:
            return datetime.strptime(text.strip(), fmt)
        except Exception:
            pass
    return None

def clean_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)         
    s = re.sub(r"https?://\S+", " ", s)    
    s = re.sub(r"www\.\S+", " ", s)
    s = re.sub(r"[^A-Za-z0-9\s]", " ", s)   
    s = re.sub(r"\s+", " ", s).strip()
    return s.lower()
