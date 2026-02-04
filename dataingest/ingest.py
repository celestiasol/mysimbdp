from flask import Flask, request, jsonify
import requests
import os
import pandas as pd
from io import StringIO
from jsonschema import validate, ValidationError
import logging

LOG_DIR = "/logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=f"{LOG_DIR}/ingestion.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

app = Flask(__name__)
COREDMS_API = os.getenv("COREDMS_API", "http://mysimbdp-coredms:5000")

def validate_records(records):
    valid = []
    invalid = []
    SCHEMA = {
        "type": "object",
        "properties": {
            "tenantId": {"type": "string"},
            "timestamp": {"type": ["string", "number"]},
            "value": {"type": ["number", "string"]},
        },
        "required": ["tenantId"],
        "additionalProperties": True
    }

    for r in records:
        try:
            validate(instance=r, schema=SCHEMA)
            valid.append(r)
        except ValidationError as e:
            invalid.append({"record": r, "error": e.message})

    return valid, invalid

def parse_csv(content):
    df = pd.read_csv(StringIO(content.text))
    return df.to_dict(orient="records")


@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "mysimbdp-dataingest is running"}), 200


@app.route("/ingest", methods=["POST"])
def ingest():
    data = request.get_json()

    if not data or "dataset_url" not in data:
        logger.warning("Request missing dataset_url")
        return jsonify({"error": "dataset_url is required"}), 400

    dataset_url = data["dataset_url"]
    tenant_id = data.get("tenantId", "unknown")

    logger.info(f"Starting ingestion | tenant={tenant_id} | source={dataset_url}")

    # Download dataset
    try:
        resp = requests.get(dataset_url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Dataset fetch failed | tenant={tenant_id} | error={e}")
        return jsonify({
            "error": "Unable to fetch dataset",
            "details": "dataset_url invalid or unreachable"
        }), 400

    # Detect file type
    content_type = resp.headers.get("Content-Type", "")
    file_name = dataset_url.lower()

    try:
        if "text/csv" in content_type or file_name.endswith(".csv"):
            records = parse_csv(resp)
            logger.info(f"Parsed {len(records)} records | tenant={tenant_id}")

        else:
            return jsonify({
                "error": "Unsupported file format",
                "supported": "csv"
            }), 415

    except Exception as e:
        return jsonify({
            "error": "Failed to parse dataset",
            "details": str(e)
        }), 400
    
    tenant_id = data.get("tenantId")
    if tenant_id:
        for rec in records:
            rec["tenantId"] = tenant_id

    # Validate
    valid_records, invalid_records = validate_records(records)

    logger.info(f"Valid records={len(valid_records)} | Invalid={len(invalid_records)} | tenant={tenant_id}")

    if not valid_records:
        return jsonify({
            "error": "All records failed validation",
            "invalid_records": invalid_records[:5]
        }), 400

    # Send only valid records
    try:
        r = requests.post(f"{COREDMS_API}/data", json={"records": valid_records})
        r.raise_for_status()

        logger.info(f"Ingestion SUCCESS | tenant={tenant_id} | inserted={len(valid_records)}")


    except requests.exceptions.ConnectionError:
        logger.error(f"CoreDMS write FAILED | tenant={tenant_id} | error={e}")
        return jsonify({"error": "CoreDMS service unreachable"}), 503

    except requests.exceptions.Timeout:
        logger.error(f"CoreDMS write FAILED | tenant={tenant_id} | error={e}")
        return jsonify({"error": "CoreDMS request timed out"}), 504

    except requests.exceptions.HTTPError as e:
        # CoreDMS responded but with error (400/500)
        logger.error(f"CoreDMS write FAILED | tenant={tenant_id} | error={e}")
        return jsonify({
            "error": "CoreDMS rejected data",
            "details": r.text
        }), r.status_code

    except Exception as e:
        # Unexpected bug in ingestion service itself
        logger.error(f"CoreDMS write FAILED | tenant={tenant_id} | error={e}")
        return jsonify({
            "error": "Unexpected ingestion error",
            "details": str(e)
        }), 500

    return jsonify({
        "status": "Ingestion completed",
        "valid_records": len(valid_records),
        "invalid_records": len(invalid_records),
        "sample_invalid": invalid_records[:3]
    }), 200



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000)
