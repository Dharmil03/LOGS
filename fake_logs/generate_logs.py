import time, random, logging, os

os.makedirs("/var/log/fake", exist_ok=True)
log_file = "/var/log/fake/app.log"

logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s')

messages = [
    "Kafka: message produced successfully",
    "K8s pod restarted",
    "DB connection failed",
    "API request timeout",
    "Transaction success",
    "Authentication error",
    "Cache hit rate low"
]

while True:
    msg = random.choice(messages)
    level = random.choice([logging.INFO, logging.WARNING, logging.ERROR])
    logging.log(level, msg)
    time.sleep(random.uniform(0.5, 2))

