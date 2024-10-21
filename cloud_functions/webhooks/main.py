import functions_framework
import os
from google.cloud import storage
from google.cloud import pubsub_v1
import json
from datetime import datetime

VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN')
BUCKET_NAME = 'strava-users'
PROJECT_ID = os.environ.get('PROJECT_ID')

storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, 'strava-activity-events')

@functions_framework.http
def webhook(request):
    if request.method == 'GET':
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
        
        store_event(event_data)
        
        return 'EVENT_RECEIVED', 200

def store_event(event):
    event_id = event.get('object_id', 'unknown')
    athlete_id = event.get('owner_id', 'unknown')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"event_{athlete_id}_{event_id}_{timestamp}.json"

    blob = bucket.blob(f'raw_events/{filename}')
    blob.upload_from_string(json.dumps(event), content_type='application/json')

    print(f"Event stored as {filename}")

    if event.get('object_type') == 'activity':
        # Include athlete_id in the message
        message_data = json.dumps({
            'event': event,
            'athlete_id': athlete_id
        }).encode('utf-8')
        publisher.publish(topic_path, message_data)
        print(f"Published event for athlete {athlete_id} to Pub/Sub")