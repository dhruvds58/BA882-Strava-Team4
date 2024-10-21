from prefect import flow, task
from google.cloud import storage
from google.cloud import bigquery
from google.cloud import pubsub_v1
import json
import pandas as pd
from typing import Dict, Any, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@task
def extract_data(athlete_id: str, activity_id: str) -> Dict[str, Any]:
    logger.info(f"Extracting data for athlete {athlete_id} and activity {activity_id}")
    storage_client = storage.Client()
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
        # Define columns to keep
    columns_to_keep = [
        'resource_state', 'name', 'distance', 'moving_time', 'elapsed_time',
        'total_elevation_gain', 'type', 'sport_type', 'workout_type', 'id',
        'start_date', 'start_date_local', 'timezone', 'achievement_count',
        'kudos_count', 'comment_count', 'athlete_count', 'photo_count',
        'trainer', 'commute', 'manual', 'private', 'visibility', 'flagged',
        'gear_id', 'start_latlng', 'end_latlng', 'average_speed', 'max_speed',
        'average_cadence', 'average_watts', 'max_watts', 'weighted_average_watts',
        'kilojoules', 'device_watts', 'has_heartrate', 'average_heartrate',
        'max_heartrate', 'elev_high', 'elev_low', 'upload_id', 'upload_id_str',
        'external_id', 'pr_count', 'total_photo_count', 'suffer_score',
        'calories', 'perceived_exertion', 'prefer_perceived_exertion',
        'device_name', 'embed_token', 'athlete.id', 'gear.primary',
        'gear.name', 'gear.distance'
    ]

    # Create DataFrame with only the columns we want
    df = pd.json_normalize(activity_data, sep='_')[columns_to_keep]

    # Rename columns to match our schema
    df = df.rename(columns={
        'athlete_id': 'athlete_id',
        'gear_primary': 'gear_primary',
        'gear_name': 'gear_name',
        'gear_distance': 'gear_distance'
    })

    # Convert date columns
    date_columns = ['start_date', 'start_date_local']
    for col in date_columns:
        df[col] = pd.to_datetime(df[col])

    # Calculate elevation change
    df['elevation_change'] = df['elev_high'] - df['elev_low']

    # Extract time-based features
    df['day_of_week'] = df['start_date_local'].dt.day_name()
    df['hour'] = df['start_date_local'].dt.hour
    df['month'] = df['start_date_local'].dt.month_name()
    logger.info(f"Transformed activity data into DataFrame with shape {df.shape}")
    return df

@task
def transform_laps_data(laps_data: List[Dict[str, Any]]) -> pd.DataFrame:
    logger.info(f"Transforming laps data with {len(laps_data)} laps")
    # Define columns to keep
    columns_to_keep = [
        'id', 'resource_state', 'name', 'elapsed_time', 'moving_time',
        'start_date', 'start_date_local', 'distance', 'average_speed',
        'max_speed', 'lap_index', 'split', 'start_index', 'end_index',
        'total_elevation_gain', 'average_cadence', 'device_watts',
        'average_watts', 'average_heartrate', 'max_heartrate', 'pace_zone',
        'activity.id', 'activity.visibility', 'activity.resource_state',
        'athlete.id', 'athlete.resource_state'
    ]

    # Create DataFrame with only the columns we want
    df = pd.json_normalize(laps_data, sep='_')[columns_to_keep]

    # Rename columns to match our schema
    df = df.rename(columns={
        'activity_id': 'activity_id',
        'activity_visibility': 'activity_visibility',
        'activity_resource_state': 'activity_resource_state',
        'athlete_id': 'athlete_id',
        'athlete_resource_state': 'athlete_resource_state'
    })

    # Convert date columns
    date_columns = ['start_date', 'start_date_local']
    for col in date_columns:
        df[col] = pd.to_datetime(df[col])

    # Extract time-based features
    df['start_day'] = df['start_date_local'].dt.day
    df['start_hour'] = df['start_date_local'].dt.hour
    df['start_weekday'] = df['start_date_local'].dt.weekday
    logger.info(f"Transformed laps data into DataFrame with shape {df.shape}")
    return df

@task
def load_to_bigquery(df: pd.DataFrame, table_id: str) -> None:
    logger.info(f"Loading {len(df)} rows into BigQuery table {table_id}")
    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(autodetect=True)
    
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()

    logger.info(f"Successfully loaded {len(df)} rows into {table_id}")

@flow
def etl_flow(athlete_id: str, activity_id: str):
    logger.info(f"Starting ETL flow for athlete {athlete_id} and activity {activity_id}")
    try:
        # Extract
        data = extract_data(athlete_id, activity_id)
        
        # Transform
        transformed_activity = transform_activity_data(data['activity'])
        transformed_laps = transform_laps_data(data['laps'])
        
        # Load
        load_to_bigquery(transformed_activity, "strava-etl.strava_data.activities")
        load_to_bigquery(transformed_laps, "strava-etl.strava_data.laps")
        
        logger.info("ETL flow completed successfully")
    except Exception as e:
        logger.error(f"An error occurred during the ETL flow: {str(e)}")
        raise

if __name__ == "__main__":
    etl_flow("test_athlete_id", "test_activity_id")