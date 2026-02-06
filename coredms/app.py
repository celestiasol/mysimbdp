from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import threading
import time
import os
import logging

# -------------------- Setup --------------------
LOG_DIR = "/logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=f"{LOG_DIR}/ingestion.log",
    level=logging.INFO,
    format="%(asctime)s | COREDMS | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongos:27020/mysimbdp?retryWrites=true&w=majority")
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client["mysimbdp"]
collection = db["tenant_data"]

# -------------------- Helpers --------------------
def wait_for_primary(client, timeout=180):
    """Wait for a writable primary in the cluster."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            hello = client.admin.command("hello")
            if hello.get("isWritablePrimary"):
                logger.info(f"Mongo primary is ready: {hello.get('primary')}")
                return True
            logger.info("Mongo reachable but no primary yet")
        except ServerSelectionTimeoutError:
            logger.warning("Mongo not reachable yet")
        time.sleep(1)
    return False

def wait_for_shards(client, min_shards=1, timeout=180):
    """Wait until Mongos reports at least `min_shards`."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            shards = client.admin.command("listShards")
            shard_count = len(shards.get("shards", []))
            if shard_count >= min_shards:
                logger.info(f"Mongos sees {shard_count} shard(s): {[s['_id'] for s in shards['shards']]}")
                return True
            logger.info(f"Mongos reachable but shards not ready yet: {shards}")
        except Exception as e:
            logger.warning(f"Cannot list shards yet: {e}")
        time.sleep(2)
    return False

def get_primary_node():
    try:
        status = client.admin.command("hello")
        return status.get("primary", "unknown")
    except Exception:
        return "unknown"

# -------------------- Monitoring --------------------
def monitor_mongos(client, logger, interval=5):
    """Monitor Mongos for availability and known shards."""
    while True:
        try:
            hello = client.admin.command("hello")
            shards = hello.get("hosts", [])
            logger.info(f"[MONGOS] Mongos reachable, shards: {shards}")
        except Exception as e:
            logger.error(f"[MONGOS] Cannot reach mongos: {e}")
        time.sleep(interval)

def monitor_shard(shard_name, client, logger, interval=5):
    """Monitor a shard's replica set: primary changes and node up/down."""
    last_primary = None
    known_nodes = set()

    while True:
        try:
            hello = client.admin.command("hello")
            primary = hello.get("primary")
            hosts = set(hello.get("hosts", []))

            if primary != last_primary:
                logger.warning(f"[SHARD {shard_name}] Primary changed: {last_primary} → {primary}")
                last_primary = primary

            down_nodes = known_nodes - hosts
            up_nodes = hosts - known_nodes

            for node in down_nodes:
                logger.error(f"[SHARD {shard_name}] Node DOWN: {node}")
            for node in up_nodes:
                logger.info(f"[SHARD {shard_name}] Node UP: {node}")

            known_nodes = hosts
        except ServerSelectionTimeoutError:
            logger.error(f"[SHARD {shard_name}] Cannot reach shard")
        except Exception as e:
            logger.error(f"[SHARD {shard_name}] Unexpected error: {e}")

        time.sleep(interval)

def start_hybrid_monitor(logger):
    """Start monitoring Mongos + all shard replica sets."""
    mongos_client = MongoClient("mongodb://mongos:27020")
    shard_clients = {
        "rs0": MongoClient("mongodb://mongo1:27018,mongo2:27018,mongo3:27018/?replicaSet=rs0"),
    }

    threading.Thread(target=monitor_mongos, args=(mongos_client, logger), daemon=True).start()
    for shard_name, client in shard_clients.items():
        threading.Thread(target=monitor_shard, args=(shard_name, client, logger), daemon=True).start()

# -------------------- Startup --------------------
if not wait_for_primary(client):
    logger.error("Mongo primary not ready, exiting...")
    exit(1)

if not wait_for_shards(client):
    logger.error("Mongos does not see any shards, exiting...")
    exit(1)

collection.create_index("tenantId")
collection.create_index("timestamp")
logger.info("Database and indexes are ready")

start_hybrid_monitor(logger)

# -------------------- Flask App --------------------
app = Flask(__name__)

@app.route("/data", methods=["POST"])
def insert_data():
    primary_node = get_primary_node()
    write_start = time.time()
    data = request.get_json()

    if not data or "records" not in data:
        return jsonify({"error": "records field required"}), 400
    records = data["records"]
    if not isinstance(records, list) or len(records) == 0:
        return jsonify({"error": "records must be a non-empty list"}), 400

    try:
        result = collection.insert_many(records)
        duration = time.time() - write_start
        throughput = len(records) / duration if duration > 0 else 0

        logger.info(
            f"WRITE_METRICS | primary_node={primary_node} | "
            f"records={len(records)} | duration_sec={duration:.3f} | throughput_rps={throughput:.2f}"
        )

        return jsonify({"inserted_count": len(result.inserted_ids)}), 201

    except ServerSelectionTimeoutError:
        return jsonify({"error": "MongoDB primary unavailable, please retry"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/data", methods=["GET"])
def get_data():
    tenant_id = request.args.get("tenantId")
    limit = int(request.args.get("limit", 50))
    if not tenant_id:
        return jsonify({"error": "tenantId query param required"}), 400

    try:
        results = list(collection.find({"tenantId": tenant_id}, {"_id": 0}).limit(limit))
        if not results:
            return jsonify({"error": "No data found for this tenant"}), 404
        return jsonify({"count": len(results), "data": results}), 200

    except ServerSelectionTimeoutError:
        return jsonify({"error": "MongoDB primary unavailable, please retry"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

# -------------------- Main --------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
