import functions_framework
import requests
import json
import base64
import os
import sys

PREFECT_API_URL = os.environ.get('PREFECT_API_URL')
PREFECT_API_KEY = os.environ.get('PREFECT_API_KEY')
PREFECT_DEPLOYMENT_ID = os.environ.get('PREFECT_DEPLOYMENT_ID')

@functions_framework.cloud_event
def trigger_prefect_flow(cloud_event):
    print("Function triggered. Starting execution.")
    
    # Check for required environment variables
    if not PREFECT_API_KEY:
        print("Error: PREFECT_API_KEY is not set")
        return 'Error: PREFECT_API_KEY is not set', 500
    if not PREFECT_DEPLOYMENT_ID:
        print("Error: PREFECT_DEPLOYMENT_ID is not set")
        return 'Error: PREFECT_DEPLOYMENT_ID is not set', 500

    try:
        print("Decoding Pub/Sub message.")
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
        message_data = json.loads(pubsub_message)
        
        print(f"Parsed message data: {message_data}")
        
        athlete_id = str(message_data['athlete_id'])
        activity_id = str(message_data['activity_id'])
        
        print(f"Athlete ID: {athlete_id}, Activity ID: {activity_id}")
        
        headers = {
            "Authorization": f"Bearer {PREFECT_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "parameters": {
                "athlete_id": athlete_id,
                "activity_id": activity_id
            }
        }
        
        print("Preparing to send request to Prefect API.")
        print(f"API URL: {PREFECT_API_URL}")
        print(f"Deployment ID: {PREFECT_DEPLOYMENT_ID}")
        
        url = f"{PREFECT_API_URL}/deployments/{PREFECT_DEPLOYMENT_ID}/create_flow_run"
        print(f"Full request URL: {url}")
        
        response = requests.post(
            url,
            headers=headers,
            json=payload
        )
        
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")
        
        if response.status_code == 404:
            print("Error: Deployment not found. Please check the PREFECT_DEPLOYMENT_ID.")
            return 'Error: Deployment not found', 404
        
        response.raise_for_status()
        flow_run = response.json()
        print(f"Triggered Prefect flow run with id: {flow_run.get('id', 'Unknown')}")
        return 'Prefect flow triggered', 200
    except requests.exceptions.RequestException as e:
        print(f"Request error occurred: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        if hasattr(e, 'response'):
            print(f"Response status code: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
        return f'Error: {str(e)}', 500
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print("Traceback:", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return f'Error: {str(e)}', 500

print("Function definition complete.")