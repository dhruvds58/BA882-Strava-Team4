import functions_framework
from google.cloud import storage
from google.cloud import pubsub_v1
import json
import requests
import base64
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
PREDICT_TOPIC = 'projects/strava-etl/topics/make-prediction'

# Define columns needed for prediction
PREDICTION_COLUMNS = ['distance', 'moving_time', 'average_heartrate']

def refresh_access_token(athlete_id, refresh_token):
    """Refresh the access token using the provided refresh token."""
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }
    
    logger.info("Requesting new access token...")
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
        blob.upload_from_string(json.dumps(tokens))
        
        logger.info(f"Access token refreshed for athlete {athlete_id}")
        return access_token
    else:
        logger.error(f"Failed to refresh access token: {response_data}")
        raise ValueError("Failed to refresh access token")

def get_access_token(athlete_id):
    """Retrieve or refresh the access token for a given athlete ID."""
    blob = bucket.blob(f'tokens/{athlete_id}.json')
    if not blob.exists():
        raise ValueError(f"No token found for athlete {athlete_id}")
    
    tokens = json.loads(blob.download_as_string())
    access_token = tokens.get('access_token')
    refresh_token = tokens.get('refresh_token')

    # Test the current access token
    headers = {"Authorization": f"Bearer {access_token}"}
    test_url = "https://www.strava.com/api/v3/athlete"
    test_response = requests.get(test_url, headers=headers)
    
    if test_response.status_code == 401:  # Token expired
        logger.info("Access token expired, refreshing...")
        access_token = refresh_access_token(athlete_id, refresh_token)
    
    return access_token

def fetch_and_store_data(url, athlete_id, activity_id, data_type):
    """Fetch data from Strava API and store it in Cloud Storage."""
    access_token = get_access_token(athlete_id)
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        logger.info(f"Received {data_type} data for activity {activity_id}")
        
        # Store data
        blob = bucket.blob(f'{data_type}/athlete_{athlete_id}_activity_{activity_id}_{data_type}.json')
        blob.upload_from_string(json.dumps(data))
        
        logger.info(f"{data_type.capitalize()} data stored for athlete {athlete_id}, activity {activity_id}")
        return True, data
    else:
        logger.error(f"Failed to fetch {data_type} data: {response.text}")
        return False, None

def prepare_prediction_data(activity_data):
    """Extract only the necessary columns for prediction."""
    prediction_data = {}
    for column in PREDICTION_COLUMNS:
        if column in activity_data:
            prediction_data[column] = activity_data[column]
        else:
            logger.warning(f"Column {column} not found in activity data")
            logger.info(f"Available columns: {list(activity_data.keys())}")
    logger.info(f"Prepared prediction data: {prediction_data}")
    return prediction_data

@functions_framework.cloud_event
def fetch_activity_data(cloud_event):
    """Cloud Function triggered by Pub/Sub message to fetch activity and laps data."""
    try:
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
        message_data = json.loads(pubsub_message)
        logger.info(f"Received message data: {message_data}")
        
        event = message_data['event']
        athlete_id = message_data['athlete_id']
        
        if event['object_type'] != 'activity':
            return 'Not an activity event', 200

        activity_id = event['object_id']
        logger.info(f"Processing activity {activity_id} for athlete {athlete_id}")
        
        # Fetch and store detailed activity data
        activity_url = f"https://www.strava.com/api/v3/activities/{activity_id}"
        activity_success, activity_data = fetch_and_store_data(activity_url, athlete_id, activity_id, 'activities')

        # Fetch and store laps data
        laps_url = f"{activity_url}/laps"
        laps_success, _ = fetch_and_store_data(laps_url, athlete_id, activity_id, 'laps')

        if activity_success and activity_data:
            try:
                # Prepare prediction data
                prediction_data = prepare_prediction_data(activity_data)
                
                # Create prediction message
                predict_message = json.dumps({
                    'athlete_id': athlete_id,
                    'activity_id': activity_id,
                    'prediction_data': prediction_data
                }).encode('utf-8')
                
                logger.info(f"Publishing prediction message for activity {activity_id}")
                publisher.publish(PREDICT_TOPIC, predict_message)
                logger.info(f"Prediction trigger sent for athlete {athlete_id}, activity {activity_id}")
                
            except Exception as e:
                logger.error(f"Error preparing/sending prediction data: {str(e)}")
        
        # Send ETL message
        if activity_success or laps_success:
            etl_message = json.dumps({
                'athlete_id': athlete_id,
                'activity_id': activity_id,
            }).encode('utf-8')
            
            publisher.publish(ETL_TOPIC, etl_message)
            logger.info(f"ETL trigger sent for athlete {athlete_id}, activity {activity_id}")
            
        return 'Success', 200
        
    except Exception as e:
        logger.error(f"Error in fetch_activity_data: {str(e)}")
        return f'Error: {str(e)}', 500