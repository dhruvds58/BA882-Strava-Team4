import functions_framework
import os
from google.cloud import storage
import json
from datetime import datetime

VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN')
BUCKET_NAME = 'raw-events'

storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

@functions_framework.http
def webhook(request):
    if request.method == 'GET':
        # Verification logic (keep this as is)
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode and token:
            if mode == 'subscribe' and token == VERIFY_TOKEN:
                print("WEBHOOK_VERIFIED")
                return {"hub.challenge": challenge}
            else:
                return 'Forbidden', 403
        return 'Bad Request', 400

    elif request.method == 'POST':
        event_data = request.get_json()
        print("Received webhook event:", event_data)
        
        # Store the event data
        store_event(event_data)
        
        return 'EVENT_RECEIVED', 200

def store_event(event):
    # Generate a unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"event_{timestamp}.json"

    # Create a new blob and upload the file contents
    blob = bucket.blob(filename)
    blob.upload_from_string(json.dumps(event), content_type='application/json')

    print(f"Event stored as {filename}")