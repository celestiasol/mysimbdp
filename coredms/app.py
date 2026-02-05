from flask import Flask, request, jsonify
from pymongo import MongoClient
import os, logging
import time
from pymongo.errors import ServerSelectionTimeoutError
import threading

LOG_DIR = "/logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=f"{LOG_DIR}/ingestion.log",
    level=logging.INFO,
    format="%(asctime)s | COREDMS | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)



MONGO_URI = os.getenv("MONGO_URI") + "&retryWrites=true"
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

db = client["mysimbdp"]
collection = db["tenant_data"]

def monitor_mongo_cluster(client, logger, interval=1):
    """
    Monitor the MongoDB replica set for:
      - Primary changes
      - Node up/down
      - Election in progress / primary unavailable
    Logs everything to the provided logger.
    """
    last_primary = None
    known_nodes = set()

    while True:
        try:
            hello = client.admin.command("hello")
            primary = hello.get("primary")
            hosts = set(hello.get("hosts", []))
            is_writable = hello.get("isWritablePrimary", False)
            election_in_progress = hello.get("electionId") is not None and not is_writable

            # Log primary status
            if primary != last_primary:
                if primary:
                    logger.warning(f"[CLUSTER] PRIMARY changed: {last_primary} → {primary}")
                else:
                    logger.warning(f"[CLUSTER] No PRIMARY currently elected")
                last_primary = primary

            # Log election in progress
            if election_in_progress:
                logger.info(f"[CLUSTER] Election in progress, no writable primary yet")

            # Detect node up/down
            down_nodes = known_nodes - hosts
            up_nodes = hosts - known_nodes

            for node in down_nodes:
                logger.error(f"[CLUSTER] Node DOWN: {node}")

            for node in up_nodes:
                logger.info(f"[CLUSTER] Node UP: {node}")

            known_nodes = hosts

            # Debug info
            logger.debug(f"[CLUSTER DEBUG] primary={primary} | isWritable={is_writable} | hosts={hosts}")

        except ServerSelectionTimeoutError:
            logger.error("[CLUSTER] Cannot reach MongoDB cluster")
        except Exception as e:
            logger.error(f"[CLUSTER] Unexpected error: {e}")

        time.sleep(interval)


def get_primary_node():
    try:
        status = client.admin.command("hello")
        return status.get("primary", "unknown")
    except Exception:
        return "unknown"

def wait_for_primary(client, timeout=180):
    start = time.time()
    while time.time() - start < timeout:
        try:
            hello = client.admin.command("hello")
            if hello.get("isWritablePrimary"):
                logger.info("Mongo primary is ready")
                return True
            logger.info("Mongo reachable but no primary yet")
        except ServerSelectionTimeoutError:
            logger.warning("Mongo not reachable yet")
        time.sleep(1)
    return False


# usage
if not wait_for_primary(client):
    print("Could not connect to Mongo primary, exiting...")
    exit(1)

# Helpful indexes for performance
collection.create_index("tenantId")
collection.create_index("timestamp")

monitor_thread = threading.Thread(
    target=monitor_mongo_cluster,
    args=(client, logger),
    daemon=True
)
monitor_thread.start()

app = Flask(__name__)

# ---------------- WRITE API ----------------
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

        write_end = time.time()
        duration = write_end - write_start
        throughput = len(records) / duration if duration > 0 else 0

        logger.info(
            f"WRITE_METRICS | "
            f"primary_node={primary_node} | "
            f"records={len(records)} | "
            f"duration_sec={duration:.3f} | "
            f"throughput_rps={throughput:.2f}"
        )

        return jsonify({
            "inserted_count": len(result.inserted_ids)
        }), 201

    except ServerSelectionTimeoutError:
        return jsonify({"error": "MongoDB primary unavailable, please retry"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------- READ API ----------------
@app.route("/data", methods=["GET"])
def get_data():
    tenant_id = request.args.get("tenantId")
    limit = int(request.args.get("limit", 50))

    if not tenant_id:
        return jsonify({"error": "tenantId query param required"}), 400

    try:
        results = list(collection.find(
            {"tenantId": tenant_id},
            {"_id": 0}   # hide mongo id
        ).limit(limit))

        if not results:
            return jsonify({
                "error": "No data found for this tenant"
            }), 404

        return jsonify({
            "count": len(results),
            "data": results
        }), 200

    except ServerSelectionTimeoutError:
        return jsonify({"error": "MongoDB primary unavailable, please retry"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Health check
@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
