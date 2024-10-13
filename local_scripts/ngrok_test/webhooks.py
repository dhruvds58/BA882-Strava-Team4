import os
import requests
from dotenv import load_dotenv

load_dotenv()

def create_subscription(client_id, client_secret, callback_url, verify_token):
    url = 'https://www.strava.com/api/v3/push_subscriptions'
    
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'callback_url': callback_url,
        'verify_token': verify_token
    }
    
    print(f"Sending POST request to {url}")
    print(f"Data: {data}")
    
    response = requests.post(url, data=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    return response

# Load environment variables
client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
callback_url = os.getenv('CALLBACK_URL')
verify_token = os.getenv('VERIFY_TOKEN')

print(f"Client ID: {client_id}")
print(f"Client Secret: {client_secret[:5]}...") # Print only first 5 characters for security
print(f"Callback URL: {callback_url}")
print(f"Verify Token: {verify_token}")

# Create subscription
response = create_subscription(client_id, client_secret, callback_url, verify_token)

# Check if subscription was successful
if response.status_code == 201:
    print("Webhook subscription created successfully!")
else:
    print("Failed to create webhook subscription. Please check the error message above.")