import re
import os
import math
from datetime import datetime
from pathlib import Path
from collections import Counter

from flask import Flask, render_template, request
from bs4 import BeautifulSoup
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
STATIC_FOLDER = 'static'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# ---------------- HELPER FUNCTIONS ----------------
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
    weights = {
        "Search": 1,
        "YouTube": 2,
        "Maps": 3,
        "Shopping": 2,
        "Discover": 2,
        "Other": 1
    }

    base_risk = sum(weights.get(cat, 1) * math.log(1 + count)
                    for cat, count in categories.items())

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
        return ("Low", "green", "Low tracking detected.",
                ["Review settings in your mobile.",
                 "Use incognito for sensitive searches.",
                 "Clear browsing history periodically."],
                risk_percent)
    elif total_risk <= 10:
        return ("Medium", "#ffcc00", "Moderate tracking detected.",
                ["Turn off Location History.",
                 "Revoke unused third-party app permissions.",
                 "Use a privacy-focused browser (Brave/Firefox)."],
                risk_percent)
    else:
        return ("High", "red", "Heavy tracking detected recently.",
                ["Pause Web & App Activity.",
                 "Delete recent activity from My Activity.",
                 "Consider a VPN and disable ad personalization."],
                risk_percent)


def get_risk_comment(risk_score):
    if risk_score <= 25:
        return "👻 You're almost invisible… or are you? 🤨"
    elif risk_score <= 50:
        return "🍕📺 Google knows your fav snacks & late-night YouTube."
    elif risk_score <= 75:
        return "😐 Bro… Google knows you better than your mom."
    else:
        return "😱 Damn! Your whole life is recorded by Google 😭"


def get_personality_type(risk_score):
    if risk_score <= 25:
        return "🕵️‍♂️ The Ghost — you leave almost no trace."
    elif risk_score <= 50:
        return "🙂 The Casual User — you share enough, not too much."
    elif risk_score <= 75:
        return "📲 The Over-Sharer — constant life updates to Google."
    else:
        return "📖 The Transparent Soul — Google has your biography."


def analyze_html_takeout(filepath: str):
    categories = {"Search": 0, "YouTube": 0, "Maps": 0,
                  "Shopping": 0, "Discover": 0, "Other": 0}
    times = []

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")

    whole_text = clean_text(soup.get_text(" ", strip=True))

    buckets = {
        "Search": [r"\bsearch(ed|es|ing)?\b", r"\bgoogle search\b", r"\bquery\b"],
        "YouTube": [r"\byoutube\b", r"\bwatch(ed|ing)?\b", r"\bvideo\b"],
        "Maps": [r"\bgoogle maps\b", r"\bnavigat(e|ed|ion)\b", r"\bdirections?\b", r"\bplace\b"],
        "Shopping": [r"\bshopping\b", r"\bproduct\b", r"\bcart\b", r"\bbuy\b", r"\border\b"],
        "Discover": [r"\bdiscover\b", r"\brecommended\b", r"\bfor you\b"]
    }

    for cat, patterns in buckets.items():
        count = 0
        for p in patterns:
            count += len(re.findall(p, whole_text))
        categories[cat] += count

    if sum(categories.values()) == 0:
        categories["Other"] = 1

    time_like = []
    for t in soup.select("time"):
        if t.get("datetime"):
            time_like.append(t["datetime"])
        elif t.text:
            time_like.append(t.text)

    time_like += re.findall(
        r"[A-Z][a-z]+ \d{1,2}, \d{4} (?:at |, )\d{1,2}:\d{2}(?: [AP]M)?",
        soup.get_text(" "))

    for raw in time_like:
        dt = parse_datetime(raw)
        if dt:
            times.append(dt)

    return categories, times


def analyze_plain_text(filepath: str):
    categories = {"Search": 0, "YouTube": 0, "Maps": 0,
                  "Shopping": 0, "Discover": 0, "Other": 0}
    times = []

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        txt = clean_text(f.read())

    if not txt.strip():
        categories["Other"] = 1
        return categories, times

    buckets = {
        "Search": [r"\bsearch\b", r"\bgoogle search\b", r"\bquery\b"],
        "YouTube": [r"\byoutube\b", r"\bwatch\b", r"\bvideo\b"],
        "Maps": [r"\bmaps\b", r"\bnavigate\b", r"\bdirection\b", r"\bplace\b"],
        "Shopping": [r"\bshopping\b", r"\bproduct\b", r"\bbuy\b", r"\border\b"],
        "Discover": [r"\bdiscover\b", r"\brecommended\b", r"\bfor you\b"]
    }
    for cat, patterns in buckets.items():
        for p in patterns:
            categories[cat] += len(re.findall(p, txt))

    if sum(categories.values()) == 0:
        categories["Other"] = 1

    return categories, times


def analyze_file(filepath: str):
    ext = os.path.splitext(filepath)[1].lower()
    if ext in (".html", ".htm"):
        return analyze_html_takeout(filepath)
    else:
        return analyze_plain_text(filepath)


# ---------------- ROUTES ----------------
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        if "file" not in request.files:
            return "No file part", 400
        file = request.files["file"]
        if not file.filename:
            return "No selected file", 400

        filename = file.filename
        filepath = Path(app.config["UPLOAD_FOLDER"]) / filename
        file.save(filepath)

        categories, activity_times = analyze_file(str(filepath))

        risk_level, risk_color, risk_message, risk_suggestions, risk_percent = calculate_risk(
            categories, recent_activities=activity_times
        )
        risk_comment = get_risk_comment(risk_percent)
        personality = get_personality_type(risk_percent)

        filtered = {k: v for k, v in categories.items() if v > 0}
        if not filtered:
            filtered = {"Other": 1}

        plt.figure(figsize=(6, 6))
        plt.pie(list(filtered.values()),
                labels=list(filtered.keys()),
                autopct='%1.1f%%',
                startangle=90)
        plt.title('Activity Breakdown')
        chart_name = 'activity_chart.png'
        plt.savefig(os.path.join(STATIC_FOLDER, chart_name), bbox_inches="tight")
        plt.close()

        return render_template(
            "index.html",
            filename=filename,
            categories=categories,
            chart_url=chart_name,
            risk_level=risk_level,
            risk_color=risk_color,
            suggestion=risk_message,
            risk_suggestions=risk_suggestions,
            risk_percent=risk_percent,
            risk_comment=risk_comment,
            personality=personality
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Internal Server Error: {e}"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
