import functions_framework
import base64
import json
import os
from prefect.client import get_client

@functions_framework.cloud_event
async def trigger_prefect_flow(cloud_event):
    pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
    message_data = json.loads(pubsub_message)
    
    athlete_id = message_data['athlete_id']
    activity_id = message_data['activity_id']

    async with get_client() as client:
        deployment_id = await client.get_deployment_id(name="strava-etl-flow")
        flow_run = await client.create_flow_run_from_deployment(
            deployment_id, parameters={"athlete_id": athlete_id, "activity_id": activity_id}
        )
        print(f"Created flow run {flow_run.id}")

    return 'Prefect flow triggered', 200
