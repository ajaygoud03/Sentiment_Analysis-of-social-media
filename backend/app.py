import os
import tempfile
import boto3
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from dotenv import load_dotenv




# --- Load environment variables from .env file ---
load_dotenv()

# --- Flask app ---
app = Flask(__name__, static_folder="/frontend/build", static_url_path="/")
CORS(app,resources={r"/api/*": {"origins": "*"}})  # allows all dev requests to /api/*

# --- Environment Variables ---
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
MODEL_KEY = os.getenv("MODEL_KEY", "mbert-sentiment-best")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")

print("🔍 Debug ENV:")
print("AWS_ACCESS_KEY_ID:", bool(AWS_ACCESS_KEY_ID))
print("AWS_SECRET_ACCESS_KEY:", "SET" if AWS_SECRET_ACCESS_KEY else "MISSING")
print("AWS_REGION:", AWS_REGION)
print("S3_BUCKET_NAME:", S3_BUCKET_NAME)
print("MODEL_KEY:", MODEL_KEY)
print("X_BEARER_TOKEN:", "SET" if X_BEARER_TOKEN else "MISSING")

# --- Model Loader ---
def download_model_from_s3():
    """Download model files from S3 into a temp directory and return path."""
    s3 = boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    tmp_dir = tempfile.mkdtemp()

    resp = s3.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=MODEL_KEY)
    if "Contents" not in resp:
        raise ValueError("No files found in S3 model folder!")

    for obj in resp["Contents"]:
        file_key = obj["Key"]
        file_name = os.path.basename(file_key)
        if file_name:  # skip folder entries
            local_path = os.path.join(tmp_dir, file_name)
            print(f"⬇️ Downloading {file_key} → {local_path}")
            s3.download_file(S3_BUCKET_NAME, file_key, local_path)

    print("📦 Model downloaded to:", tmp_dir)
    print("📂 Files:", os.listdir(tmp_dir))
    return tmp_dir

# --- Load Model ---
sentiment_pipeline = None
try:
    model_dir = download_model_from_s3()
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir, local_files_only=True)
    sentiment_pipeline = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer, device=-1)
    print("✅ Model loaded successfully from S3!")
except Exception as e:
    print(f"❌ Error loading model from S3: {e}")

# --- Routes ---
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Sentiment API is running!"})

@app.route("/analyze", methods=["POST"])
def analyze():
    if sentiment_pipeline is None:
        return jsonify({"error": "Model not loaded"}), 500

    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' in request"}), 400

    text = data["text"]
    result = sentiment_pipeline(text)
    return jsonify(result)

@app.route("/api/trending", methods=["GET"])
def trending():
    """Fetch top 10 breaking/news tweets and analyze them."""
    if not X_BEARER_TOKEN:
        return jsonify({"error": "X_BEARER_TOKEN missing"}), 500
    if sentiment_pipeline is None:
        return jsonify({"error": "Model not loaded"}), 500

    headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
    url = "https://api.twitter.com/2/tweets/search/recent"
    params = {
        "query": "(#breakingnews OR #news) lang:en -is:retweet",
        "max_results": 10,
        "tweet.fields": "id,text,created_at,author_id"
    }

    r = requests.get(url, headers=headers, params=params)
    if r.status_code != 200:
        return jsonify({"error": "Failed to fetch tweets", "details": r.text}), r.status_code

    tweets = r.json().get("data", [])
    results = []
    for t in tweets:
        text = t["text"]
        analysis = sentiment_pipeline(text)[0]
        results.append({
            "id": t["id"],
            "text": text,
            "sentiment": analysis["label"],
            "score": round(float(analysis["score"]), 4)
        })

    return jsonify(results)

@app.route("/api/fetch_and_analyze", methods=["POST"])
def fetch_and_analyze():
    """Fetch a single tweet by URL or ID and analyze sentiment."""
    if not X_BEARER_TOKEN:
        return jsonify({"error": "X_BEARER_TOKEN missing"}), 500
    if sentiment_pipeline is None:
        return jsonify({"error": "Model not loaded"}), 500

    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "Missing 'url'"}), 400

    url = data["url"]
    tweet_id = url.split("/")[-1]  # extract last part of URL
    headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
    api_url = f"https://api.twitter.com/2/tweets/{tweet_id}"
    params = {"tweet.fields": "id,text,created_at,author_id"}

    r = requests.get(api_url, headers=headers, params=params)
    if r.status_code != 200:
        return jsonify({"error": "Failed to fetch tweet", "details": r.text}), r.status_code

    tweet = r.json().get("data", {})
    if not tweet:
        return jsonify({"error": "Tweet not found"}), 404

    analysis = sentiment_pipeline(tweet["text"])[0]
    return jsonify({
        "id": tweet["id"],
        "text": tweet["text"],
        "sentiment": analysis["label"],
        "score": round(float(analysis["score"]), 4)
    })

# --- Serve React frontend (only in production) ---
#@app.route("/<path:path>")
#def serve_react(path):
 #   return send_from_directory(app.static_folder, path)

#@app.errorhandler(404)
#def not_found(e):
 #   return send_from_directory(app.static_folder, "index.html")
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    full_path = os.path.join(app.static_folder, path)
    if path != "" and os.path.exists(full_path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")


# --- Start Server (local only) ---
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
