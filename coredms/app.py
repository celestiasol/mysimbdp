from flask import Flask, request, jsonify
from pymongo import MongoClient
import os
import time
from pymongo.errors import ServerSelectionTimeoutError


app = Flask(__name__)

MONGO_URI = os.getenv("MONGO_URI") + "&retryWrites=true"
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

db = client["mysimbdp"]
collection = db["tenant_data"]

def wait_for_primary(client, timeout=30):
    """Wait until a primary node is available."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            ismaster = client.admin.command("ismaster")
            if ismaster.get("ismaster"):
                print("Mongo primary is ready")
                return True
            else:
                print("Mongo connected but not primary, retrying...")
        except ServerSelectionTimeoutError:
            print("Mongo not ready, retrying...")
        time.sleep(1)
    return False

# usage
if not wait_for_primary(client):
    print("Could not connect to Mongo primary, exiting...")
    exit(1)

# Helpful indexes for performance
collection.create_index("tenantId")
collection.create_index("timestamp")


# ---------------- WRITE API ----------------
@app.route("/data", methods=["POST"])
def insert_data():
    data = request.get_json()

    if not data or "records" not in data:
        return jsonify({"error": "records field required"}), 400

    records = data["records"]

    if not isinstance(records, list) or len(records) == 0:
        return jsonify({"error": "records must be a non-empty list"}), 400

    try:
        result = collection.insert_many(records)
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
