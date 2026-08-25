import os
import io
from flask import Flask, request, jsonify
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from azure.storage.blob import BlobServiceClient

app = Flask(__name__)

STORAGE_CONN_STRING = os.getenv("STORAGE_CONN_STRING")
CONTAINER_NAME = "invoices"

def generate_pdf(order_data):
    """Generates an in-memory PDF invoice using ReportLab."""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, f"INVOICE - Order #{order_data.get('order_id')}")
    
    p.setFont("Helvetica", 12)
    p.drawString(100, 720, f"Customer: {order_data.get('customer_name', 'N/A')}")
    p.drawString(100, 700, f"Item: {order_data.get('item', 'N/A')}")
    p.drawString(100, 680, f"Amount: ${order_data.get('amount', 0)}")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

@app.route('/dapr/subscribe', methods=['GET'])
def subscribe():
    """Tells Dapr which Service Bus topic to subscribe to."""
    subscriptions = [{
        'pubsubname': 'order-pubsub',
        'topic': 'order-events',
        'route': 'order-listener'
    }]
    return jsonify(subscriptions)

@app.route('/order-listener', methods=['POST'])
def process_invoice():
    """Triggered by Dapr when a new order event arrives."""
    event = request.json
    order_data = event.get('data', {})
    order_id = order_data.get('order_id')

    # 1. Generate Invoice PDF
    pdf_buffer = generate_pdf(order_data)

    # 2. Upload directly to Azure Blob Storage
    if STORAGE_CONN_STRING:
        blob_service_client = BlobServiceClient.from_connection_string(STORAGE_CONN_STRING)
        blob_client = blob_service_client.get_blob_client(
            container=CONTAINER_NAME, 
            blob=f"invoice_{order_id}.pdf"
        )
        blob_client.upload_blob(pdf_buffer, overwrite=True)
        print(f"Invoice uploaded to Azure Blob Storage for Order #{order_id}")

    return jsonify({"success": True}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)