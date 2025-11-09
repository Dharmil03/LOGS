import os
import time
import threading
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import chromadb
import hashlib

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"

LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100")
PROM_URL = os.getenv("PROM_URL", "http://prometheus:9090")

CHROMA_API_KEY = os.getenv("CHROMA_API_KEY")
CHROMA_TENANT = os.getenv("CHROMA_TENANT")

db_from_env = os.getenv("CHROMA_DATABASE", "")
if db_from_env and not db_from_env.endswith(" "):
    CHROMA_DATABASE = db_from_env + " "
elif not db_from_env:
    CHROMA_DATABASE = "Dharmil "
else:
    CHROMA_DATABASE = db_from_env

LOKI_QUERY = '{job="fake_logs"}'
STREAM_POLL_INTERVAL = 3.0

app = Flask(__name__)
CORS(app)


print("\n" + "="*70)
print("🔵 Connecting to ChromaDB Cloud...")
print(f"   Tenant: {CHROMA_TENANT}")
print(f"   Database: '{CHROMA_DATABASE}' (length: {len(CHROMA_DATABASE)})")
print("="*70)

try:
    client = chromadb.CloudClient(
        api_key=CHROMA_API_KEY,
        tenant=CHROMA_TENANT,
        database=CHROMA_DATABASE
    )
    
    logs_col = client.get_or_create_collection(
        name="system_logs",
        metadata={"description": "System logs from observability stack"}
    )
    
    print(f"✅ ChromaDB Connected!")
    print(f"   Collection: {logs_col.name}")
    print(f"   Current count: {logs_col.count()}")
    print("="*70 + "\n")
    
except Exception as e:
    print(f"❌ ChromaDB Connection Failed: {e}")
    raise

_last_ts = str(int((time.time() - 600) * 1_000_000_000))  # Start 10 minutes ago
_total_added = 0
_total_processed = 0
_streamer_running = True
_last_fetch_time = None

def generate_unique_id(timestamp, log_line, index):
    """Generate truly unique ID"""
    content = f"{timestamp}_{log_line}_{index}_{time.time()}"
    return hashlib.sha256(content.encode()).hexdigest()[:32]

def stream_logs():
    global _last_ts, _total_added, _total_processed, _last_fetch_time
    
    print("\n" + "="*70)
    print("🔄 STARTING LOG STREAMER")
    print(f"   Loki URL: {LOKI_URL}")
    print(f"   Query: {LOKI_QUERY}")
    print(f"   Poll Interval: {STREAM_POLL_INTERVAL}s")
    print(f"   Starting from: {_last_ts}")
    print("="*70 + "\n")
    
    poll_count = 0
    consecutive_errors = 0
    
    while _streamer_running:
        try:
            poll_count += 1
            current_time = int(time.time() * 1_000_000_000)
            
            # Check Loki connectivity first
            try:
                health_check = requests.get(f"{LOKI_URL}/ready", timeout=3)
                if health_check.status_code != 200:
                    print(f"⚠️  Poll #{poll_count}: Loki not ready (status: {health_check.status_code})")
                    time.sleep(STREAM_POLL_INTERVAL)
                    continue
            except Exception as e:
                print(f"⚠️  Poll #{poll_count}: Cannot reach Loki: {e}")
                consecutive_errors += 1
                if consecutive_errors <= 3:
                    print(f"   💡 Make sure Loki container is running: docker-compose ps loki")
                time.sleep(STREAM_POLL_INTERVAL)
                continue
            
            params = {
                "query": LOKI_QUERY,
                "start": _last_ts,
                "end": str(current_time),
                "limit": 1000,
                "direction": "forward"
            }
            
            print(f"\n📡 Poll #{poll_count}: Fetching logs from Loki...")
            print(f"   Time range: {_last_ts} to {current_time}")
            
            res = requests.get(
                f"{LOKI_URL}/loki/api/v1/query_range",
                params=params,
                timeout=15
            )
            
            _last_fetch_time = time.time()
            
            if res.status_code != 200:
                print(f"❌ Poll #{poll_count}: Loki error {res.status_code}: {res.text[:200]}")
                time.sleep(STREAM_POLL_INTERVAL)
                continue
            
            data = res.json()
            results = data.get("data", {}).get("result", [])
            
            print(f"   Received {len(results)} streams from Loki")
            
            if not results:
                print(f"   ⏳ No new logs. ChromaDB count: {logs_col.count()}")
                if poll_count == 1:
                    print(f"   💡 Check if fake-logs container is running and generating logs")
                    print(f"   💡 Check Promtail: docker-compose logs promtail | tail -20")
                consecutive_errors = 0
                time.sleep(STREAM_POLL_INTERVAL)
                continue
            
            new_docs, new_metas, new_ids = [], [], []
            max_ts = None
            
            for stream_idx, stream in enumerate(results):
                labels = stream.get("stream", {})
                values = stream.get("values", [])
                
                print(f"   📦 Stream {stream_idx+1}: {len(values)} log entries, labels: {labels}")
                
                for value_idx, (ts, log_line) in enumerate(values):
                    ts_int = int(ts)
                    
                    # Skip if already processed
                    if ts_int <= int(_last_ts):
                        continue
                    
                    # Generate unique ID with multiple factors
                    unique_id = generate_unique_id(ts, log_line, len(new_ids))
                    
                    new_ids.append(unique_id)
                    new_docs.append(log_line)
                    new_metas.append({
                        "timestamp": ts,
                        "job": labels.get("job", "unknown"),
                        "labels": str(labels),
                        "processed_at": str(int(time.time())),
                        "stream_index": str(stream_idx),
                        "value_index": str(value_idx)
                    })
                    
                    if max_ts is None or ts_int > int(max_ts):
                        max_ts = ts
            
            if new_docs:
                _total_processed += len(new_docs)
                
                print(f"\n   💾 Attempting to add {len(new_docs)} logs to ChromaDB...")
                
                try:
                    # Use upsert to handle any duplicates
                    logs_col.upsert(
                        ids=new_ids,
                        documents=new_docs,
                        metadatas=new_metas
                    )
                    
                    _total_added += len(new_docs)
                    current_count = logs_col.count()
                    
                    print(f"   ✅ SUCCESS! Added {len(new_docs)} logs to ChromaDB")
                    print(f"   📊 Stats:")
                    print(f"      - Session processed: {_total_processed}")
                    print(f"      - Session added: {_total_added}")
                    print(f"      - ChromaDB total: {current_count}")
                    print(f"      - Sample log: {new_docs[0][:100]}...")
                    
                    consecutive_errors = 0
                    
                except Exception as e:
                    print(f"   ❌ ChromaDB upsert failed: {e}")
                    print(f"      Error type: {type(e).__name__}")
                    consecutive_errors += 1
            else:
                print(f"   ⚠️  All logs were duplicates (already processed)")
            
            # Update timestamp
            if max_ts:
                _last_ts = str(int(max_ts) + 1)
                print(f"   🕐 Updated last timestamp to: {_last_ts}")
            
        except Exception as e:
            print(f"\n❌ Poll #{poll_count}: Unexpected error: {e}")
            print(f"   Error type: {type(e).__name__}")
            consecutive_errors += 1
        
        time.sleep(STREAM_POLL_INTERVAL)

# Start streamer thread
streamer_thread = threading.Thread(target=stream_logs, daemon=True)
streamer_thread.start()
print("✅ Streamer thread started\n")

# ==============================================================
# 📊 ROUTES
# ==============================================================

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    try:
        return jsonify({
            "status": "ok",
            "chromadb_count": logs_col.count(),
            "logs_processed": _total_processed,
            "logs_added": _total_added,
            "streamer_running": _streamer_running,
            "last_fetch": _last_fetch_time
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/logs", methods=["GET"])
def get_logs():
    """Fetch logs directly from Loki"""
    try:
        limit = request.args.get("limit", 100, type=int)
        
        # Get last hour of logs
        end_time = int(time.time() * 1_000_000_000)
        start_time = end_time - (3600 * 1_000_000_000)  # 1 hour ago
        
        params = {
            "query": LOKI_QUERY,
            "limit": limit,
            "start": str(start_time),
            "end": str(end_time),
            "direction": "backward"  # Get newest first
        }
        
        print(f"\n🌐 /logs endpoint called (limit={limit})")
        
        res = requests.get(
            f"{LOKI_URL}/loki/api/v1/query_range",
            params=params,
            timeout=10
        )
        
        if res.status_code == 200:
            data = res.json()
            result_count = len(data.get("data", {}).get("result", []))
            print(f"   ✅ Returned {result_count} streams from Loki")
            return jsonify(data)
        else:
            print(f"   ❌ Loki error: {res.status_code}")
            return jsonify({
                "error": f"Loki returned status {res.status_code}",
                "details": res.text
            }), res.status_code
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/stats", methods=["GET"])
def stats():
    """Get detailed stats"""
    try:
        count = logs_col.count()
        sample = logs_col.peek(limit=5)
        
        return jsonify({
            "chromadb": {
                "total": count,
                "sample_ids": sample.get("ids", []),
                "sample_docs": sample.get("documents", [])
            },
            "streamer": {
                "processed": _total_processed,
                "added": _total_added,
                "running": _streamer_running,
                "last_fetch": _last_fetch_time
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/debug/loki", methods=["GET"])
def debug_loki():
    """Debug endpoint to check Loki directly"""
    try:
        # Check Loki health
        health = requests.get(f"{LOKI_URL}/ready", timeout=5)
        
        # Get label names
        labels = requests.get(f"{LOKI_URL}/loki/api/v1/labels", timeout=5)
        
        # Get series for our query
        series = requests.get(
            f"{LOKI_URL}/loki/api/v1/series",
            params={"match[]": LOKI_QUERY},
            timeout=5
        )
        
        return jsonify({
            "loki_health": health.status_code,
            "labels": labels.json() if labels.ok else labels.text,
            "series": series.json() if series.ok else series.text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/chat", methods=["POST"])
def chat():
    """AI chat endpoint"""
    data = request.get_json()
    user_msg = data.get("message", "").strip()
    
    if not user_msg:
        return jsonify({"error": "Empty message"}), 400
    
    print(f"\n💬 Chat query: {user_msg}")
    
    try:
        count = logs_col.count()
        print(f"   ChromaDB has {count} documents")
        
        if count == 0:
            context = "⚠️ No logs in ChromaDB yet"
            logs_found = 0
        else:
            result = logs_col.query(
                query_texts=[user_msg],
                n_results=min(15, count)
            )
            docs = result.get("documents", [[]])[0]
            metas = result.get("metadatas", [[]])[0]
            
            context = "\n".join([
                f"[{m.get('timestamp', '')}] {d}" 
                for d, m in zip(docs, metas)
            ])
            
            if not context:
                context = "No relevant logs found"
            
            logs_found = len(docs)
            print(f"   Found {logs_found} relevant logs")
    except Exception as e:
        context = f"ChromaDB query error: {e}"
        logs_found = 0
        print(f"   ❌ Query error: {e}")
    
    try:
        prom_res = requests.get(
            f"{PROM_URL}/api/v1/query",
            params={"query": "up"},
            timeout=5
        )
        metrics = prom_res.json() if prom_res.ok else {"error": "Failed"}
    except:
        metrics = {"error": "Prometheus unavailable"}
    
    prompt = f"""You are an observability AI assistant.

User Question: {user_msg}

Relevant Logs:
{context}

Metrics:
{metrics}

Provide diagnosis and suggestions."""

    try:
        gemini_res = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30
        )
        
        if gemini_res.ok:
            answer = gemini_res.json()["candidates"][0]["content"]["parts"][0]["text"]
        else:
            answer = f"Gemini error: {gemini_res.status_code}"
    except Exception as e:
        answer = f"Gemini request failed: {e}"
    
    return jsonify({
        "answer": answer,
        "logs_found": logs_found,
        "total_in_db": count
    })

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 Starting Flask on 0.0.0.0:5000")
    print("📍 Available endpoints:")
    print("   - GET  /health")
    print("   - GET  /logs")
    print("   - GET  /stats")
    print("   - GET  /debug/loki")
    print("   - POST /chat")
    print("="*70 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
