# backend/app.py
import os
import tempfile
import boto3
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from dotenv import load_dotenv

# Load .env for local dev (Cloud Run will provide env vars via secrets)
load_dotenv()

app = Flask(__name__, static_folder="../frontend/build", static_url_path="/")
CORS(app, resources={r"/api/*": {"origins": "*"}})

# --- Environment ---
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
MODEL_KEY = os.getenv("MODEL_KEY", "mbert-sentiment-best")  # prefix in bucket (no leading slash)
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")

print("🔍 Debug ENV:")
print("AWS_ACCESS_KEY_ID:", bool(AWS_ACCESS_KEY_ID))
print("AWS_SECRET_ACCESS_KEY:", "SET" if AWS_SECRET_ACCESS_KEY else "MISSING")
print("AWS_REGION:", AWS_REGION)
print("S3_BUCKET_NAME:", S3_BUCKET_NAME)
print("MODEL_KEY:", MODEL_KEY)
print("X_BEARER_TOKEN:", "SET" if X_BEARER_TOKEN else "MISSING")


# Basic checks (fail early in dev)
if not X_BEARER_TOKEN:
    raise ValueError("Missing X_BEARER_TOKEN in environment (set for Twitter API)")

# Helper label mapping (customize to your model labels)
LABEL_MAP = {"LABEL_0": "Negative", "LABEL_1": "Neutral", "LABEL_2": "Positive"}
def human_label(label):
    return LABEL_MAP.get(label, label)

def download_model_from_s3():
    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME, MODEL_KEY]):
        raise ValueError("Missing AWS creds / bucket / MODEL_KEY env vars")

    s3 = boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    tmp_dir = tempfile.mkdtemp()
    prefix = MODEL_KEY.rstrip("/") + "/"
    print("🔍 Listing objects under prefix:", prefix)
    resp = s3.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)
    if "Contents" not in resp:
        raise ValueError(f"No files found in S3 model folder at prefix '{prefix}'")

    for obj in resp["Contents"]:
        file_key = obj["Key"]
        file_name = os.path.basename(file_key)
        if not file_name:
            continue
        local_path = os.path.join(tmp_dir, file_name)
        print(f"⬇️ Downloading {file_key} → {local_path}")
        s3.download_file(S3_BUCKET_NAME, file_key, local_path)

    print("📦 Model downloaded to:", tmp_dir)
    print("📂 Files:", os.listdir(tmp_dir))
    return tmp_dir

# Load model (at container start)
sentiment_pipeline = None
try:
    model_dir = download_model_from_s3()
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir, local_files_only=True)
    sentiment_pipeline = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer, device=-1)
    print("✅ Model loaded successfully from S3!")
except Exception as e:
    print("❌ Error loading model from S3:", e)
    sentiment_pipeline = None

# Routes
@app.route("/", methods=["GET"])
def home():
    # serve frontend if present
    index = os.path.join(os.path.dirname(__file__), "..", "frontend", "build", "index.html")
    if os.path.exists(index):
        return send_from_directory(os.path.dirname(index), "index.html")
    return jsonify({"message": "Sentiment API is running!"})

@app.route("/api/trending", methods=["GET"])
def get_trending_posts():
    limit = int(request.args.get("limit", 10))
    url = "https://api.twitter.com/2/tweets/search/recent"
    query = "(#news OR #breaking) lang:en -is:retweet"
    params = {"query": query, "max_results": limit, "tweet.fields": "text,id"}
    headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}

    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        posts = [t["text"] for t in data.get("data", [])]
        if sentiment_pipeline:
            preds = sentiment_pipeline(posts)
            results = []
            for text, p in zip(posts, preds):
                results.append({
                    "text": text,
                    "sentiment": human_label(p.get("label")),
                    "score": float(p.get("score", 0.0))
                })
            return jsonify(results)
        else:
            return jsonify([{"text": t} for t in posts])
    except Exception as e:
        print("❌ Error fetching trends:", e)
        return jsonify({"error": "Could not fetch recent posts", "details": str(e)}), 500

@app.route("/api/fetch_and_analyze", methods=["POST"])
def fetch_and_analyze():
    if not sentiment_pipeline:
        return jsonify({"error": "Model not available"}), 500
    body = request.get_json() or {}
    url = body.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    try:
        tweet_id = url.rstrip("/").split("/")[-1].split("?")[0]
        headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
        r = requests.get(f"https://api.twitter.com/2/tweets/{tweet_id}", headers=headers, params={"tweet.fields":"text"}, timeout=10)
        r.raise_for_status()
        text = r.json()["data"]["text"]
    except Exception as e:
        print("❌ Error fetching single tweet:", e)
        return jsonify({"error":"Could not fetch tweet", "details": str(e)}), 404
    try:
        p = sentiment_pipeline(text)[0]
        return jsonify({"postText": text, "sentiment": human_label(p.get("label")), "score": float(p.get("score", 0.0))})
    except Exception as e:
        print("❌ Analysis error:", e)
        return jsonify({"error": f"Analysis error: {e}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print("Starting local Flask on port", port)
    app.run(host="0.0.0.0", port=port)
