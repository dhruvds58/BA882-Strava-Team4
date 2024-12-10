import pandas as pd
import functions_framework
from google.cloud import bigquery
from google.cloud import storage
import joblib
import io

@functions_framework.http
def populate_existing_labels(request):
    # Initialize BigQuery client
    client = bigquery.Client(project="strava-etl")
    table_id = "strava-etl.strava_data.clustering_labels_1"
    temp_table_id = "strava-etl.strava_data.temp_run_types"
    
    # Query the table to fetch existing rows
    query = "SELECT id, distance, moving_time, average_heartrate FROM `strava-etl.strava_data.clustering_labels_1`"
    df = client.query(query).to_dataframe()

    # Load scaler and model from GCS
    storage_client = storage.Client(project="strava-etl")
    bucket_name = "strava-models"

    scaler_blob = storage_client.bucket(bucket_name).blob("models/scaler_1.joblib")
    model_blob = storage_client.bucket(bucket_name).blob("models/kmeans_model_1.joblib")

    scaler_bytes = scaler_blob.download_as_bytes()
    scaler = joblib.load(io.BytesIO(scaler_bytes))

    model_bytes = model_blob.download_as_bytes()
    model = joblib.load(io.BytesIO(model_bytes))

    # Prepare data for clustering
    features = df[["distance", "moving_time", "average_heartrate"]]
    scaled_features = scaler.transform(features)
    labels = model.predict(scaled_features)

    # Map cluster labels to run types
    cluster_labels = {
        0: "Marathon Prep",
        1: "Medium-Distance Steady Run",
        2: "Low-Intensity Run",
        3: "Long Tempo Run"
    }
    df["run_type_str"] = [cluster_labels[label] for label in labels]

    # Load updated run_type_str values into a temporary table
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    load_job = client.load_table_from_dataframe(df[["id", "run_type_str"]], temp_table_id, job_config=job_config)
    load_job.result()  # Wait for the load job to complete

    # Use a MERGE statement to update the main table from the temporary table
    merge_query = f"""
    MERGE `{table_id}` T
    USING `{temp_table_id}` S
    ON T.id = S.id
    WHEN MATCHED THEN
      UPDATE SET T.run_type_str = S.run_type_str
    """

    client.query(merge_query).result()

    return "Run types updated successfully", 200
