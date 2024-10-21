from prefect import flow, task
from prefect_gcp import GcpCredentials
from google.cloud import storage
from google.cloud import bigquery
import json
import pandas as pd
from typing import Dict, Any, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@task
def get_gcp_creds():
    return GcpCredentials.load("gcp-creds")

@task
def extract_data(gcp_credentials: GcpCredentials, athlete_id: str, activity_id: str) -> Dict[str, Any]:
    logger.info(f"Extracting data for athlete {athlete_id} and activity {activity_id}")
    storage_client = storage.Client(credentials=gcp_credentials.get_credentials_from_service_account())
    bucket = storage_client.bucket('strava-users')
    activity_blob = bucket.blob(f'activities/athlete_{athlete_id}_activity_{activity_id}_activities.json')
    laps_blob = bucket.blob(f'laps/athlete_{athlete_id}_activity_{activity_id}_laps.json')
    
    activity_data = json.loads(activity_blob.download_as_string())
    laps_data = json.loads(laps_blob.download_as_string())
    
    logger.info(f"Extracted activity data with {len(activity_data)} fields")
    logger.info(f"Extracted laps data with {len(laps_data)} laps")
    
    return {
        'activity': activity_data,
        'laps': laps_data
    }

@task
def transform_activity_data(activity_data: Dict[str, Any]) -> pd.DataFrame:
    logger.info("Transforming activity data")
    
    columns_to_keep = [
        'resource_state', 'name', 'distance', 'moving_time', 'elapsed_time',
        'total_elevation_gain', 'type', 'sport_type', 'workout_type', 'id',
        'start_date', 'start_date_local', 'timezone', 'achievement_count',
        'kudos_count', 'comment_count', 'athlete_count', 'photo_count',
        'trainer', 'commute', 'manual', 'private', 'visibility', 'flagged',
        'gear_id', 'gear_primary', 'gear_name', 'gear_distance',
        'start_latlng', 'end_latlng', 'average_speed', 'max_speed',
        'average_cadence', 'average_watts', 'max_watts', 'weighted_average_watts',
        'kilojoules', 'device_watts', 'has_heartrate', 'average_heartrate',
        'max_heartrate', 'elev_high', 'elev_low', 'upload_id', 'upload_id_str',
        'external_id', 'pr_count', 'total_photo_count', 'suffer_score',
        'calories', 'perceived_exertion', 'prefer_perceived_exertion',
        'device_name', 'embed_token', 'athlete_id'
    ]
    
    df = pd.json_normalize(activity_data, sep='_')[columns_to_keep]

    date_columns = ['start_date', 'start_date_local']
    for col in date_columns:
        df[col] = pd.to_datetime(df[col])

    int_columns = ['resource_state', 'moving_time', 'elapsed_time', 
                   'workout_type', 'id', 'achievement_count', 'kudos_count', 
                   'comment_count', 'athlete_count', 'photo_count', 
                   'trainer', 'commute', 'manual', 'private', 'flagged', 
                   'upload_id', 'upload_id_str', 'pr_count', 
                   'total_photo_count', 'prefer_perceived_exertion']

    for col in int_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce', downcast='integer')

    df['elevation_change'] = df['elev_high'] - df['elev_low']

    df['day_of_week'] = df['start_date_local'].dt.day_name()
    df['hour'] = df['start_date_local'].dt.hour
    df['month'] = df['start_date_local'].dt.month_name()

    if 'start_latlng' in df.columns and 'end_latlng' in df.columns:
        df['start_latlng'] = df['start_latlng'].apply(
            lambda x: ','.join(map(str, x)) if isinstance(x, list) else x
        )
        df['end_latlng'] = df['end_latlng'].apply(
            lambda x: ','.join(map(str, x)) if isinstance(x, list) else x
        )

    logger.info(f"Transformed activity data into DataFrame with shape {df.shape}")
    return df

@task
def transform_laps_data(laps_data: List[Dict[str, Any]]) -> pd.DataFrame:
    logger.info("Transforming laps data")
    
    columns_to_keep = [
        'id', 'resource_state', 'name', 'elapsed_time', 'moving_time',
        'start_date', 'start_date_local', 'distance', 'average_speed',
        'max_speed', 'lap_index', 'total_elevation_gain', 'average_cadence',
        'device_watts', 'average_watts', 'average_heartrate', 'max_heartrate',
        'pace_zone'
    ]
    
    df = pd.json_normalize(laps_data, sep='_')[columns_to_keep]
    
    date_columns = ['start_date', 'start_date_local']
    for col in date_columns:
        df[col] = pd.to_datetime(df[col])

    logger.info(f"Transformed laps data into DataFrame with shape {df.shape}")
    return df

@task
def load_to_bigquery(gcp_credentials: GcpCredentials, df: pd.DataFrame, table_id: str) -> None:
    logger.info(f"Loading {len(df)} rows into BigQuery table {table_id}")
    client = bigquery.Client(credentials=gcp_credentials.get_credentials_from_service_account())
    job_config = bigquery.LoadJobConfig(autodetect=True)
    
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()

    logger.info(f"Successfully loaded {len(df)} rows into {table_id}")

@flow
def etl_flow(athlete_id: str, activity_id: str):
    logger.info(f"Starting ETL flow for athlete {athlete_id} and activity {activity_id}")
    try:
        gcp_creds = get_gcp_creds()
        data = extract_data(gcp_creds, athlete_id, activity_id)
        transformed_activity = transform_activity_data(data['activity'])
        transformed_laps = transform_laps_data(data['laps'])
        load_to_bigquery(gcp_creds, transformed_activity, "strava-etl.strava_data.activities")
        load_to_bigquery(gcp_creds, transformed_laps, "strava-etl.strava_data.laps")
        logger.info("ETL flow completed successfully")
    except Exception as e:
        logger.error(f"An error occurred during the ETL flow: {str(e)}")
        raise

if __name__ == "__main__":
    etl_flow("57248538", "12709400031")