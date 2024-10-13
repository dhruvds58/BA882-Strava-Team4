# Local Testing with ngrok

This document describes how to test the webhook receiver locally using ngrok.

## Setup

1. Install ngrok
2. Install Python dependencies:
   ```
   pip install -r local_scripts/ngrok_test/requirements.txt
   ```

## Running the Local Server

1. Start the Flask app:
   ```
   python local_scripts/ngrok_test/app.py
   ```
2. In a new terminal, start ngrok:
   ```
   ngrok http 5000
   ```
3. Use the ngrok URL as your webhook callback URL when setting up the Strava subscription for testing.

## Testing

1. Perform actions on Strava (create/update activities)
2. Check the Flask app console for incoming webhook events

Remember to update your Strava subscription to your Cloud Function URL when moving to production.