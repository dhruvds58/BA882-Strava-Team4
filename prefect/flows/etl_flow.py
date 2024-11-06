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
    
    # Extract activity_id and athlete_id before normalizing
    activity_id = laps_data[0]['activity']['id']
    athlete_id = laps_data[0]['athlete']['id']
    
    df = pd.json_normalize(laps_data, sep='_')
    
    # Add IDs as new columns
    df['activity_id'] = activity_id
    df['athlete_id'] = athlete_id
    
    # Group columns logically
    identifier_columns = [
        'id',                    # Lap ID
        'activity_id',          # Reference to parent activity
        'athlete_id',           # Reference to athlete
        'lap_index',            # Order of the lap
        'split',                # Split number
        'resource_state'        # API resource state
    ]
    
    name_columns = [
        'name'                  # Lap name
    ]
    
    timing_columns = [
        'elapsed_time',         # Total time including stops
        'moving_time',          # Active time
        'start_date',          # UTC timestamp
        'start_date_local',    # Local timestamp
        'start_index',         # Starting point in activity stream
        'end_index'            # Ending point in activity stream
    ]
    
    distance_speed_columns = [
        'distance',            # Distance in meters
        'average_speed',       # Average speed
        'max_speed',          # Maximum speed
        'pace_zone'           # Pace zone classification
    ]
    
    power_columns = [
        'device_watts',        # Whether power meter was used
        'average_watts',       # Average power output
    ]
    
    biometric_columns = [
        'average_cadence',     # Average cadence
        'average_heartrate',   # Average heart rate
        'max_heartrate'        # Maximum heart rate
    ]
    
    elevation_columns = [
        'total_elevation_gain' # Total climbing in meters
    ]
    
    # Combine all columns
    columns_to_keep = (
        identifier_columns +
        name_columns +
        timing_columns +
        distance_speed_columns +
        power_columns +
        biometric_columns +
        elevation_columns
    )
    
    # Keep only the columns we want
    df = df[columns_to_keep]
    
    # Handle dates
    date_columns = ['start_date', 'start_date_local']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    
    # Convert numeric columns to appropriate types
    int_columns = identifier_columns + ['elapsed_time', 'moving_time', 
                                      'device_watts', 'pace_zone', 'split',
                                      'start_index', 'end_index']
    
    float_columns = ['distance', 'average_speed', 'max_speed', 
                    'total_elevation_gain', 'average_cadence', 
                    'average_watts', 'average_heartrate', 'max_heartrate']
    
    for col in int_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce', downcast='integer')
    
    for col in float_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Add time-based columns for analysis
    if 'start_date_local' in df.columns:
        df['start_day'] = df['start_date_local'].dt.day
        df['start_hour'] = df['start_date_local'].dt.hour
        df['start_weekday'] = df['start_date_local'].dt.weekday
    
    logger.info(f"Transformed laps data into DataFrame with shape {df.shape}")
    logger.info(f"Sample of IDs - activity_id: {activity_id}, athlete_id: {athlete_id}")
    
    return df

# @task
# def load_to_bigquery(gcp_credentials: GcpCredentials, df: pd.DataFrame, table_id: str) -> None:
#     logger.info(f"Loading {len(df)} rows into BigQuery table {table_id}")
#     client = bigquery.Client(credentials=gcp_credentials.get_credentials_from_service_account())
#     job_config = bigquery.LoadJobConfig(autodetect=True)
    
#     job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
#     job.result()

#     logger.info(f"Successfully loaded {len(df)} rows into {table_id}")

@task
def load_to_bigquery(gcp_credentials: GcpCredentials, df: pd.DataFrame, table_id: str) -> None:
    logger.info(f"Loading {len(df)} rows into BigQuery table {table_id}")
    client = bigquery.Client(credentials=gcp_credentials.get_credentials_from_service_account())
    
    # Define unique key combinations based on table
    if table_id.endswith('activities'):
        unique_keys = ['athlete_id', 'id']  # id here is activity_id
    elif table_id.endswith('laps'):
        unique_keys = ['athlete_id', 'activity_id', 'id']
    else:
        raise ValueError(f"Unknown table type: {table_id}")
        
    logger.info(f"Using composite key: {unique_keys}")
    
    # Get the destination table schema
    table = client.get_table(table_id)
    schema_fields = {field.name: field.field_type for field in table.schema}
    
    # Check for new columns in the data that aren't in BigQuery
    new_columns = set(df.columns) - set(schema_fields.keys())
    if new_columns:
        logger.info(f"Found new columns in data: {new_columns}")
        
        # Infer schema for new columns
        new_schema_fields = []
        for col in new_columns:
            if pd.api.types.is_integer_dtype(df[col]):
                field_type = 'INTEGER'
            elif pd.api.types.is_float_dtype(df[col]):
                field_type = 'FLOAT'
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                field_type = 'TIMESTAMP'
            else:
                field_type = 'STRING'
            
            new_schema_fields.append(
                bigquery.SchemaField(col, field_type, mode='NULLABLE')
            )
            schema_fields[col] = field_type
            
        # Update table schema
        if new_schema_fields:
            new_schema = table.schema + new_schema_fields
            table.schema = new_schema
            table = client.update_table(table, ['schema'])
            logger.info(f"Updated BigQuery schema with new columns: {new_columns}")
    
    # Add missing columns from BigQuery schema to DataFrame
    for field_name, field_type in schema_fields.items():
        if field_name not in df.columns:
            logger.info(f"Adding missing column {field_name} with NULL values")
            if field_type == 'INTEGER':
                df[field_name] = pd.NA
            elif field_type == 'FLOAT':
                df[field_name] = pd.NA
            elif field_type == 'STRING':
                df[field_name] = None
            elif field_type == 'TIMESTAMP':
                df[field_name] = pd.NaT
            else:
                df[field_name] = None
    
    # Configure the load job to use a temporary table
    job_config = bigquery.LoadJobConfig(
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=table.schema
    )
    
    # Create a temporary table name
    temp_table_id = f"{table_id}_temp_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Load data into temporary table
    job = client.load_table_from_dataframe(df, temp_table_id, job_config=job_config)
    job.result()
    
    # Build the composite key matching condition
    match_condition = ' AND '.join([f'T.{key} = S.{key}' for key in unique_keys])
    
    # Perform MERGE operation with composite key
    merge_query = f"""
    MERGE `{table_id}` T
    USING `{temp_table_id}` S
    ON {match_condition}
    WHEN MATCHED THEN
        UPDATE SET {', '.join([f'T.{col.name} = S.{col.name}' for col in table.schema if col.name not in unique_keys])}
    WHEN NOT MATCHED THEN
        INSERT ({', '.join([col.name for col in table.schema])})
        VALUES ({', '.join([f'S.{col.name}' for col in table.schema])})
    """
    
    # Execute merge query
    merge_job = client.query(merge_query)
    merge_job.result()
    
    # Clean up temporary table
    client.delete_table(temp_table_id)
    
    logger.info(f"Successfully loaded/updated data in {table_id}")

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
    try:
        logger.info("Starting ETL flow")
        etl_flow("57248538", "12709400031")
    except Exception as e:
        logger.error(f"Error in ETL flow: {str(e)}")
        raise