# Local Development with Ngrok

This guide explains how to use ngrok for local webhook development and testing with Strava's API.

## Overview

Ngrok creates a secure tunnel to your local machine, allowing Strava to send webhook events to your local development environment.

## Prerequisites

- Ngrok account (sign up at [ngrok.com](https://ngrok.com))
- Ngrok CLI installed
- Python development environment
- Local webhook handler code

## Setup Instructions

### 1. Install Ngrok

```bash
# MacOS (using Homebrew)
brew install ngrok

# Windows (using Chocolatey)
choco install ngrok

# Linux
snap install ngrok
```

### 2. Configure Ngrok

1. Get your authtoken from ngrok dashboard
2. Configure ngrok with your token:
```bash
ngrok config add-authtoken YOUR_AUTHTOKEN
```

### 3. Start Local Development Server

```bash
# Using Python's built-in server (example)
python -m http.server 8000

# Or using Flask
python local_scripts/webhook_server.py
```

### 4. Start Ngrok Tunnel

```bash
ngrok http 8000
```

This will display a URL like: `https://1234-your-tunnel.ngrok.io`

### 5. Configure Strava Webhook

Use the ngrok URL as your webhook callback URL:
```bash
curl -X POST https://www.strava.com/api/v3/push_subscriptions \
  -d client_id=$STRAVA_CLIENT_ID \
  -d client_secret=$STRAVA_CLIENT_SECRET \
  -d callback_url=https://your-ngrok-url/webhook \
  -d verify_token=$VERIFY_TOKEN
```

## Development Workflow

1. **Monitor Requests**:
   - Access ngrok dashboard: `http://localhost:4040`
   - View incoming webhook requests
   - Inspect request/response details

2. **Debug Webhook Events**:
```python
# Example local webhook handler
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Handle verification
        challenge = request.args.get('hub.challenge')
        return jsonify({"hub.challenge": challenge})
    elif request.method == 'POST':
        # Handle webhook event
        print("Received webhook:", request.json)
        return 'EVENT_RECEIVED', 200

if __name__ == '__main__':
    app.run(port=8000)
```

## Best Practices

1. **Security**:
   - Use HTTPS endpoints
   - Keep verify_token secure
   - Don't expose sensitive data

2. **Development**:
   - Use request logging
   - Implement error handling
   - Test various scenarios

3. **Testing**:
   - Verify webhook validation
   - Test event processing
   - Check error responses

## Troubleshooting

### Common Issues

1. **Connection Refused**:
   - Check local server is running
   - Verify correct port number
   - Restart ngrok

2. **Webhook Verification Fails**:
   - Check callback URL
   - Verify token matching
   - Monitor ngrok logs

3. **Missing Events**:
   - Check ngrok status
   - Verify subscription
   - Monitor request logs

## Additional Resources

- [Ngrok Documentation](https://ngrok.com/docs)
- [Local Development Tips](https://developers.strava.com/docs/webhooks/#local-development)