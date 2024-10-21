import functions_framework
from google.cloud import storage
import requests
import json
import os

# Strava API credentials
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REDIRECT_URI = os.environ.get('REDIRECT_URI')

# Cloud Storage settings
BUCKET_NAME = 'strava-users'

storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

def save_tokens(athlete_id, tokens):
    blob = bucket.blob(f'tokens/{athlete_id}.json')
    blob.upload_from_string(json.dumps(tokens))

@functions_framework.http
def oauth_flow(request):
    if 'code' in request.args:
        # Handle the callback from Strava
        code = request.args.get('code')
        token_url = 'https://www.strava.com/oauth/token'
        data = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code'
        }
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            tokens = response.json()
            athlete_id = tokens['athlete']['id']
            save_tokens(athlete_id, tokens)
            return 'Authorization successful. Tokens saved.'
        else:
            return f'Error: {response.status_code}, {response.text}', 400
    else:
        # Initiate the OAuth flow
        auth_url = f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope=activity:read_all"
        return f'<a href="{auth_url}">Authorize with Strava</a>'