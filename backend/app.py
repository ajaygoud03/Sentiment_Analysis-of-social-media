from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import pipeline
from dotenv import load_dotenv
import os
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Allow frontend (localhost in dev, Netlify in prod)
CORS(app, resources={r"/*": {"origins": [
    "http://localhost:3000",
    "https://your-netlify-site.netlify.app"  # replace with your Netlify site URL
]}})

# --- Bearer Token from .env ---
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")

if not X_BEARER_TOKEN:
    raise ValueError("❌ Missing X_BEARER_TOKEN in environment!")

# --- Load mBERT Model (local folder) ---
try:
    MODEL_PATH = os.path.join(os.path.dirname(__file__), "mbert-sentiment-best")
    sentiment_pipeline = pipeline("sentiment-analysis", model=MODEL_PATH, tokenizer=MODEL_PATH)
    print("✅ Model loaded successfully!")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    sentiment_pipeline = None


# --- 1. Fetch Trending Posts ---
@app.route("/api/trending", methods=["GET"])
def get_trending_posts():
    url = (
        "https://api.twitter.com/2/tweets/search/recent"
        "?query=(%23news OR %23breaking) lang:en -is:retweet"
        "&max_results=10&sort_order=relevancy"
    )
    headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}

    try:
        response = requests.get(url, headers=headers)
        print(f"📡 X API Response Status: {response.status_code}")
        response.raise_for_status()
        data = response.json()

        if "data" not in data:
            return jsonify([])

        posts = [tweet["text"] for tweet in data["data"]]
        return jsonify(posts)

    except Exception as e:
        print(f"❌ Error fetching trends: {e}")
        if "response" in locals():
            print(f"❌ Response content: {response.text}")
        return jsonify({"error": "Could not fetch recent posts"}), 500


# --- 2. Fetch Single Tweet + Analyze ---
def get_tweet_text(tweet_url):
    try:
        tweet_id = tweet_url.split("/")[-1].split("?")[0]
        headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
        url = f"https://api.twitter.com/2/tweets/{tweet_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()["data"]["text"]
    except Exception as e:
        print(f"❌ Error fetching single tweet: {e}")
        return None


@app.route("/api/fetch_and_analyze", methods=["POST"])
def fetch_and_analyze():
    if not sentiment_pipeline:
        return jsonify({"error": "Model not available"}), 500

    data = request.get_json()
    url = data.get("url", "")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    text = get_tweet_text(url)
    if not text:
        return jsonify({"error": "Could not fetch tweet"}), 404

    try:
        result = sentiment_pipeline(text)
        prediction = result[0]
        label_map = {"LABEL_0": "Negative", "LABEL_1": "Neutral", "LABEL_2": "Positive"}
        sentiment = label_map.get(prediction["label"], prediction["label"])
        score = prediction["score"]

        return jsonify({"postText": text, "sentiment": sentiment, "score": score})
    except Exception as e:
        return jsonify({"error": f"Analysis error: {e}"}), 500


import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # 5000 is default for local testing
    app.run(host="0.0.0.0", port=port)

