import functions_framework
from google.cloud import storage
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import joblib
import json
import base64
import logging
import requests
import os
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Strava API credentials
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
AUTH_URL = 'https://www.strava.com/oauth/token'

def load_model_from_gcs(blob, temp_dir):
    """Load a joblib model from GCS blob using a temporary file."""
    temp_path = os.path.join(temp_dir, 'temp_model')
    blob.download_to_filename(temp_path)
    return joblib.load(temp_path)

def refresh_access_token(refresh_token, athlete_id, storage_client):
    """Refresh the access token using the provided refresh token."""
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }
    
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
        bucket = storage_client.bucket('strava-users')
        blob = bucket.blob(f'tokens/{athlete_id}.json')
        blob.upload_from_string(json.dumps(tokens))
        
        return access_token
    else:
        raise ValueError(f"Failed to refresh access token: {response_data}")

def get_access_token(athlete_id, storage_client):
    """Retrieve or refresh the access token for a given athlete ID."""
    bucket = storage_client.bucket('strava-users')
    blob = bucket.blob(f'tokens/{athlete_id}.json')
    tokens = json.loads(blob.download_as_string())
    access_token = tokens.get('access_token')
    refresh_token = tokens.get('refresh_token')

    # Test the current access token
    headers = {"Authorization": f"Bearer {access_token}"}
    test_response = requests.get("https://www.strava.com/api/v3/athlete", headers=headers)
    
    if test_response.status_code == 401:  # Token expired
        logger.info("Access token expired, refreshing...")
        access_token = refresh_access_token(refresh_token, athlete_id, storage_client)
    
    return access_token

def update_activity_description(activity_id: str, run_type: str, access_token: str) -> None:
    """Update the activity description in Strava with the predicted run type."""
    url = f'https://www.strava.com/api/v3/activities/{activity_id}'
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # First get the current description
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        current_desc = response.json().get('description', '')
        
        # Prepare new description
        if current_desc:
            new_desc = f'Predicted Run Type: {run_type}\n\n{current_desc}'
        else:
            new_desc = f'Predicted Run Type: {run_type}'
        
        # Update the activity
        payload = {'description': new_desc}
        update_response = requests.put(url, headers=headers, json=payload)
        
        if update_response.status_code != 200:
            raise Exception(f"Failed to update activity description: {update_response.text}")
    else:
        raise Exception(f"Failed to get activity details: {response.text}")

@functions_framework.cloud_event
def make_predictions(cloud_event):
    """
    Cloud Function to predict run type from activity data and update Strava description.
    Triggered by Pub/Sub message containing activity metrics.
    """
    logger.info("Starting prediction function")
    
    try:
        # Parse the Pub/Sub message
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
        logger.info(f"Received message: {pubsub_message}")
        
        message_data = json.loads(pubsub_message)
        athlete_id = message_data.get('athlete_id')
        activity_id = message_data.get('activity_id')
        prediction_data = message_data.get('prediction_data')
        
        logger.info(f"Processing prediction for activity {activity_id}")
        logger.info(f"Prediction data: {prediction_data}")
        
        if not all([athlete_id, activity_id, prediction_data]):
            raise ValueError("Missing required data in Pub/Sub message")
        
        # Initialize storage client
        storage_client = storage.Client()
        
        # Create DataFrame from prediction data
        df = pd.DataFrame([prediction_data])
        X_new = df[['distance', 'moving_time', 'suffer_score']]
        logger.info(f"Feature data: {X_new.to_dict()}")
        
        # Load models from Cloud Storage
        bucket = storage_client.bucket('strava-models')
        
        # Create temporary directory for model files
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info("Loading models")
            scaler = load_model_from_gcs(bucket.blob('models/scaler.joblib'), temp_dir)
            kmeans = load_model_from_gcs(bucket.blob('models/kmeans_model.joblib'), temp_dir)
            
            # Make prediction
            logger.info("Making prediction")
            X_scaled = scaler.transform(X_new)
            cluster = kmeans.predict(X_scaled)[0]
            
            # Map cluster to run type
            cluster_labels = {
                0: "Low-Intensity Run",
                1: "Medium-Distance Steady Run",
                2: "Marathon Prep",
                3: "Long Tempo Run"
            }
            run_type = cluster_labels.get(cluster, "Unknown Run Type")
            logger.info(f"Predicted run type: {run_type}")
            
            # Get Strava token and update description
            access_token = get_access_token(athlete_id, storage_client)
            update_activity_description(activity_id, run_type, access_token)
            
            logger.info(f"Successfully processed activity {activity_id}")
            return ('Success', 200)
            
    except Exception as e:
        logger.error(f"Error in prediction pipeline: {str(e)}", exc_info=True)
        return (f'Error: {str(e)}', 500)