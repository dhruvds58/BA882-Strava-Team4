import os
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Get credentials from environment variables
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
CALLBACK_URL = os.getenv("CALLBACK_URL")

@app.route('/webhook', methods=['GET'])
def webhook_challenge():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print('WEBHOOK_VERIFIED')
            return jsonify({"hub.challenge": challenge})
        else:
            return 'Forbidden', 403
    return 'Bad Request', 400

@app.route('/webhook', methods=['POST'])
def webhook_event():
    print("Webhook event received!", request.json)
    # Process the webhook event here
    return 'EVENT_RECEIVED', 200

@app.route('/create_subscription', methods=['GET'])
def create_subscription():
    url = "https://www.strava.com/api/v3/push_subscriptions"
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'callback_url': CALLBACK_URL,
        'verify_token': VERIFY_TOKEN
    }
    response = requests.post(url, data=data)
    return jsonify(response.json()), response.status_code

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)