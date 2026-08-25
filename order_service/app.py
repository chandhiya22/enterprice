import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

DAPR_HTTP_PORT = os.getenv("DAPR_HTTP_PORT", "3500")
PUBSUB_NAME = "order-pubsub"
TOPIC_NAME = "order-events"
STATE_STORE_NAME = "order-statestore"

@app.route('/orders', methods=['POST'])
def create_order():
    order_data = request.json
    order_id = order_data.get("order_id")

    if not order_id:
        return jsonify({"error": "order_id is required"}), 400

    # 1. Save state to Azure Cosmos DB via Dapr State API
    state_url = f"http://localhost:{DAPR_HTTP_PORT}/v1.0/state/{STATE_STORE_NAME}"
    state_payload = [{
        "key": f"order_{order_id}",
        "value": order_data
    }]
    
    state_res = requests.post(state_url, json=state_payload)
    if state_res.status_code not in [200, 204]:
        return jsonify({"error": "Failed to save order state"}), 500

    # 2. Publish order event to Azure Service Bus via Dapr Pub/Sub API
    pubsub_url = f"http://localhost:{DAPR_HTTP_PORT}/v1.0/publish/{PUBSUB_NAME}/{TOPIC_NAME}"
    pub_res = requests.post(pubsub_url, json=order_data)

    if pub_res.status_code not in [200, 204]:
        return jsonify({"error": "Failed to publish event"}), 500

    return jsonify({
        "status": "Order Accepted",
        "order_id": order_id,
        "message": "State persisted and event published to Service Bus."
    }), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)