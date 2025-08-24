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

def calculate_risk(categories, recent_activities=None):

    weights ={
        "Search":1,
        "Youtube":2,
        "Maps":3,
        "Shopping":2,
        "Discover":2,
        "Other":1

    }
#For each category of activity, take its weight (importance) and multiply by a scaled version of how many times the user did that activity. Then add up all categories to get a single “base risk” number.
    base_risk = sum(weights.get(cat, 1) * math.log(1 + count)
                    for cat, count in categories.items())
    
 #This code calculates extra risk from recent activity, giving more weight to activities done recently. Then it adds this to the base category risk and converts the total into a percentage between 0 and 100 that represents the user’s overall data exposure.
    recent_risk = 0
    if recent_activities:
        now = datetime.now()
        for t in recent_activities:
            if isinstance(t, datetime):
                days_ago = (now - t).days
                recent_risk += math.exp(-days_ago / 7)


    total_risk = base_risk + recent_risk
    risk_percent = int(max(0, min(100, (total_risk / 15.0) * 100)))

    if total_risk <= 3:
        return (
            "Low",
            "green",
            "Low tracking detected.",
            [
                "Review settings in your mobile.",
                "Use incognito for sensitive searches.",
                "Clear browsing history periodically."
            ],
            risk_percent
        )
    elif total_risk <= 10:
        return (
            "Medium",
            "#ffcc00",
            "Moderate tracking detected.",

        [
            "Turn off Location History.",
            "Revoke unused third-party app permissions.",
            "Use a privacy-focused browser (Brave/Firefox)."
            ],
            risk_percent
        
        )
    else:
        return (
            "High",
            "red",
            "Heavy tracking detected recently.",

             [
                "Pause Web & App Activity.",
                "Delete recent activity from My Activity.",
                "Consider a VPN and disable ad personalization."
            ],
            risk_percent
        
        )
        
def get_risk_comment(risk_score):
    if risk_score <= 25:
        return "👻 You're almost invisible… or are you? 🤨"
    elif risk_score <= 50:
        return "🍕📺 Google knows your fav snacks & late-night YouTube."
    elif risk_score <= 75:
        return "😐 Bro… Google knows you better than your mom."
    else:
        return "😱 Damn! Your whole life is recorded by Google 😭"

    
