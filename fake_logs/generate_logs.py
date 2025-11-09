import time
import random
import logging
import os
import uuid

# Ensure log directory exists
os.makedirs("/var/log/fake", exist_ok=True)
log_file = "/var/log/fake/app.log"

# Configure logging
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)

# Create loggers for different services
auth_logger = logging.getLogger("auth-service")
db_logger = logging.getLogger("db-connection")
api_logger = logging.getLogger("api-gateway")
cache_logger = logging.getLogger("cache-manager")
kafka_logger = logging.getLogger("kafka-producer")

# ---------------------------------------------------------------------
# 🧠 Realistic log templates with placeholders (%s)
# ---------------------------------------------------------------------
log_templates = [
    # --- AUTH SERVICE ---
    (auth_logger, logging.WARNING, "JWT token expired for user_id=%s"),
    (auth_logger, logging.ERROR, "Failed to validate credentials for user_id=%s, reason=InvalidSignatureError"),
    (auth_logger, logging.INFO, "User login success user_id=%s session_id=%s"),
    (auth_logger, logging.ERROR, "OAuth2 callback error: state mismatch for request_id=%s"),

    # --- DATABASE ---
    (db_logger, logging.ERROR, "DB connection timeout after %sms while acquiring from pool_size=%s"),
    (db_logger, logging.WARNING, "Connection pool exhausted, waiting threads=%s"),
    (db_logger, logging.INFO, "Executed query in %sms: SELECT * FROM users WHERE id=%s"),
    (db_logger, logging.ERROR, "Deadlock detected in transaction_id=%s, rolling back"),

    # --- API GATEWAY ---
    (api_logger, logging.INFO, "Received %s request to %s"),
    (api_logger, logging.WARNING, "Slow API response %sms for endpoint %s"),
    (api_logger, logging.ERROR, "Upstream service unavailable: %s (status=%s)"),

    # --- CACHE ---
    (cache_logger, logging.INFO, "Cache hit for key=%s"),
    (cache_logger, logging.WARNING, "Cache miss for key=%s, fetching from DB"),
    (cache_logger, logging.ERROR, "Redis connection error: %s"),

    # --- KAFKA ---
    (kafka_logger, logging.INFO, "Produced message to topic=%s offset=%s"),
    (kafka_logger, logging.ERROR, "Failed to send message to topic=%s, error=TimeoutException"),
]

# ---------------------------------------------------------------------
# 🔧 Helper functions to generate dynamic content
# ---------------------------------------------------------------------
def random_str(length=8):
    return ''.join(random.choices("abcdef0123456789", k=length))

def random_endpoint():
    return random.choice(["/api/v1/login", "/api/v1/user", "/api/v1/orders", "/health", "/metrics"])

def random_topic():
    return random.choice(["auth-events", "order-stream", "user-activity", "notifications"])

def random_error():
    return random.choice(["ConnectionRefusedError", "TimeoutError", "BrokenPipeError", "InvalidQueryError"])

# ---------------------------------------------------------------------
# 🧩 Safe formatter: automatically fills all %s placeholders
# ---------------------------------------------------------------------
def safe_format(template):
    count = template.count("%s")
    values = []

    # Fill dynamic placeholders based on keywords
    if "user_id" in template and "session_id" in template:
        values = [random.randint(1000, 5000), str(uuid.uuid4())]
    elif "user_id" in template:
        values = [random.randint(1000, 5000)]
    elif "session_id" in template:
        values = [str(uuid.uuid4())]
    elif "request_id" in template:
        values = [str(uuid.uuid4())]
    elif "transaction_id" in template:
        values = [random_str(12)]
    elif "pool_size" in template:
        values = [random.randint(50, 2000), random.randint(5, 50)]
    elif "endpoint" in template and "response" in template:
        values = [random.randint(200, 3000), random_endpoint()]
    elif "endpoint" in template:
        values = [random_endpoint()]
    elif "status" in template:
        values = [random_endpoint(), random.choice(["502", "504", "503"])]
    elif "key" in template:
        values = [f"user:{random.randint(1, 500)}"]
    elif "topic" in template and "offset" in template:
        values = [random_topic(), random.randint(1000, 9999)]
    elif "topic" in template and "error" in template:
        values = [random_topic()]
    elif "query" in template:
        values = [random.randint(5, 200), random.randint(100, 2000)]
    elif "error" in template and "%s" in template:
        values = [random_error()]
    elif "request" in template and "to" in template:
        values = [random.choice(["GET", "POST", "DELETE", "PATCH"]), random_endpoint()]
    elif "%s" in template:
        values = [random.randint(100, 1000)]  # default numeric filler

    # Pad remaining placeholders safely
    while len(values) < count:
        values.append("N/A")

    try:
        return template % tuple(values)
    except Exception as e:
        return f"[FORMAT_ERROR: {e}] {template} ({values})"

if __name__ == "__main__":
    print(f"[Fake Logs] Writing to {log_file}")
    while True:
        logger, level, template = random.choice(log_templates)
        msg = safe_format(template)
        logger.log(level, msg)
        print(msg)  # Print to stdout for debugging
        time.sleep(random.uniform(0.3, 2.0))

