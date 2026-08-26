import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response

DAPR_HTTP_PORT = os.getenv("DAPR_HTTP_PORT", "3500")
PUBSUB_NAME = os.getenv("PUBSUB_NAME", "order-pubsub")
TOPIC_NAME = os.getenv("TOPIC_NAME", "order-events")
STATE_STORE_NAME = os.getenv("STATE_STORE_NAME", "order-statestore")

@app.route('/orders', methods=['POST', 'OPTIONS'])
def create_order():
    if request.method == 'OPTIONS':
        return '', 200

    order_data = request.get_json(silent=True)
    if not order_data:
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    order_id = order_data.get("order_id")
    if not order_id:
        return jsonify({"error": "order_id is required"}), 400

    description = order_data.get("description") or order_data.get("item")
    order_data["description"] = description

    # Save state via Dapr State API (fault tolerant)
    state_url = f"http://localhost:{DAPR_HTTP_PORT}/v1.0/state/{STATE_STORE_NAME}"
    state_payload = [{"key": f"order_{order_id}", "value": order_data}]
    
    try:
        requests.post(state_url, json=state_payload, timeout=3)
    except Exception as e:
        print(f"Dapr State sidecar call skipped: {e}")

    # Publish order event via Dapr Pub/Sub API (fault tolerant)
    pubsub_url = f"http://localhost:{DAPR_HTTP_PORT}/v1.0/publish/{PUBSUB_NAME}/{TOPIC_NAME}"
    try:
        requests.post(pubsub_url, json=order_data, timeout=3)
    except Exception as e:
        print(f"Dapr PubSub sidecar call skipped: {e}")

    return jsonify({
        "status": "Order Accepted",
        "order_id": order_id,
        "message": "Order processed successfully!"
    }), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
