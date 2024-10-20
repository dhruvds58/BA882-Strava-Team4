import functions_framework
from google.cloud import storage
from google.cloud import pubsub_v1
import json
import requests
import base64
import os

# Environment variables for Strava API credentials
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
AUTH_URL = 'https://www.strava.com/oauth/token'

BUCKET_NAME = 'strava-users'
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

# Set up Pub/Sub client
publisher = pubsub_v1.PublisherClient()
ETL_TOPIC = 'projects/strava-etl/topics/etl-trigger'


def refresh_access_token(athlete_id, refresh_token):
    """Refresh the access token using the provided refresh token."""
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }
    
    print("Requesting new access token...")
    response = requests.post(AUTH_URL, data=payload)
    response_data = response.json()
    
    if response.status_code == 200:
        access_token = response_data['access_token']
        new_refresh_token = response_data.get('refresh_token', refresh_token)
        
        # Update tokens in Cloud Storage
        tokens = {
            'access_token': access_token,
            'refresh_token': new_refresh_token
        }
        blob = bucket.blob(f'tokens/{athlete_id}.json')
        blob.upload_from_string(json.dumps(tokens), content_type='application/json')
        
        print(f"Access token refreshed for athlete {athlete_id}")
        return access_token
    else:
        print(f"Failed to refresh access token: {response_data}")
        raise ValueError("Failed to refresh access token")

def get_access_token(athlete_id):
    """Retrieve or refresh the access token for a given athlete ID."""
    blob = bucket.blob(f'tokens/{athlete_id}.json')
    if not blob.exists():
        raise ValueError(f"No token found for athlete {athlete_id}")
    
    tokens = json.loads(blob.download_as_string())
    access_token = tokens.get('access_token')
    refresh_token = tokens.get('refresh_token')

    # Try using the current access token, refresh if it fails
    headers = {"Authorization": f"Bearer {access_token}"}
    test_url = "https://www.strava.com/api/v3/athlete"
    test_response = requests.get(test_url, headers=headers)
    
    if test_response.status_code == 401:  # Token expired
        print("Access token expired, refreshing...")
        access_token = refresh_access_token(athlete_id, refresh_token)
    
    return access_token

def fetch_and_store_data(url, athlete_id, activity_id, data_type):
    """Fetch data from Strava API and store it in Cloud Storage."""
    access_token = get_access_token(athlete_id)
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        
        # Store data
        blob = bucket.blob(f'{data_type}/athlete_{athlete_id}_activity_{activity_id}_{data_type}.json')
        blob.upload_from_string(json.dumps(data), content_type='application/json')
        
        print(f"{data_type.capitalize()} data stored for athlete {athlete_id}, activity {activity_id}")
        return True
    else:
        print(f"Failed to fetch {data_type} data: {response.text}")
        return False

@functions_framework.cloud_event
def fetch_activity_data(cloud_event):
    """Cloud Function triggered by Pub/Sub message to fetch activity and laps data."""
    pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
    message_data = json.loads(pubsub_message)
    
    event = message_data['event']
    athlete_id = message_data['athlete_id']
    
    if event['object_type'] != 'activity':
        return 'Not an activity event', 200

    activity_id = event['object_id']
    
    # Fetch and store detailed activity data
    activity_url = f"https://www.strava.com/api/v3/activities/{activity_id}"
    activity_success = fetch_and_store_data(activity_url, athlete_id, activity_id, 'activities')

    # Fetch and store laps data
    laps_url = f"{activity_url}/laps"
    laps_success = fetch_and_store_data(laps_url, athlete_id, activity_id, 'laps')

    if activity_success or laps_success:
        # Trigger ETL process
        etl_message = json.dumps({
            'athlete_id': athlete_id,
            'activity_id': activity_id,
            'activity_success': activity_success,
            'laps_success': laps_success
        }).encode('utf-8')
        
        try:
            publisher.publish(ETL_TOPIC, etl_message)
            print(f"ETL trigger sent for athlete {athlete_id}, activity {activity_id}")
        except Exception as e:
            print(f"Failed to send ETL trigger: {str(e)}")

        if activity_success and laps_success:
            return 'Activity and laps data fetched and stored, ETL triggered', 200
        elif activity_success:
            return 'Only activity data fetched and stored, ETL triggered', 200
        elif laps_success:
            return 'Only laps data fetched and stored, ETL triggered', 200
    else:
        return 'Failed to fetch both activity and laps data', 400