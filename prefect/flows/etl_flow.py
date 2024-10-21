from prefect import flow, task
from google.cloud import storage
from google.cloud import bigquery
import json

@task
def transform_data(athlete_id, activity_id):
    # Initialize clients
    storage_client = storage.Client()
    bucket = storage_client.bucket('strava-users')

    # Read raw data
    activity_blob = bucket.blob(f'activities/athlete_{athlete_id}_activity_{activity_id}_activities.json')
    laps_blob = bucket.blob(f'laps/athlete_{athlete_id}_activity_{activity_id}_laps.json')

    activity_data = json.loads(activity_blob.download_as_string())
    laps_data = json.loads(laps_blob.download_as_string())

    # Perform transformations (simplified for this example)
    transformed_data = {
        'athlete_id': athlete_id,
        'activity_id': activity_id,
        'activity_name': activity_data.get('name'),
        'start_date': activity_data.get('start_date'),
        'distance': activity_data.get('distance'),
        'moving_time': activity_data.get('moving_time'),
        'lap_count': len(laps_data)
    }

    # Store transformed data
    transformed_blob = bucket.blob(f'transformed/athlete_{athlete_id}_activity_{activity_id}_transformed.json')
    transformed_blob.upload_from_string(json.dumps(transformed_data), content_type='application/json')

    return transformed_data

@task
def load_data(transformed_data):
    # Initialize BigQuery client
    client = bigquery.Client()

    # Specify your dataset and table
    dataset_id = 'strava_data'
    table_id = 'activities'

    # Get the table reference
    table_ref = client.dataset(dataset_id).table(table_id)

    # Load the data into BigQuery
    job_config = bigquery.LoadJobConfig()
    job_config.source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
    job_config.autodetect = True

    job = client.load_table_from_json([transformed_data], table_ref, job_config=job_config)
    job.result()  # Wait for the job to complete

    print(f"Loaded {job.output_rows} rows into {dataset_id}:{table_id}")

@flow
def etl_flow(athlete_id: str, activity_id: str):
    transformed_data = transform_data(athlete_id, activity_id)
    load_data(transformed_data)

if __name__ == "__main__":
    etl_flow("test_athlete_id", "test_activity_id")