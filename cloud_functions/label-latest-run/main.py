from google.cloud import bigquery
from google.cloud import storage
import joblib

def process_new_run(event, context):
    # Initialize BigQuery client
    client = bigquery.Client()
    table_id = "strava-etl.strava_data.clustering_labels"
    activities_table = "strava-etl.strava_data.activities"

    # Fetch the latest activity
    query = f"""
        SELECT id, start_date, distance, moving_time, average_heartrate
        FROM `{activities_table}`
        ORDER BY start_date DESC
        LIMIT 1
    """
    latest_run = client.query(query).to_dataframe()

    if latest_run.empty:
        return "No new runs found", 200

    # Load scaler and model from GCS
    storage_client = storage.Client(project="strava-etl")
    bucket_name = "strava-models"

    scaler_blob = storage_client.bucket(bucket_name).blob("models/scaler_1.joblib")
    model_blob = storage_client.bucket(bucket_name).blob("models/kmeans_model_1.joblib")

    scaler_bytes = scaler_blob.download_as_bytes()
    scaler = joblib.load(io.BytesIO(scaler_bytes))

    model_bytes = model_blob.download_as_bytes()
    model = joblib.load(io.BytesIO(model_bytes))

    # Predict cluster label for the latest run
    features = latest_run[["distance", "moving_time", "average_heartrate"]]
    scaled_features = scaler.transform(features)
    label = model.predict(scaled_features)[0]

    # Map cluster label to run type
    cluster_labels = {
        0: "Marathon Prep",
        1: "Medium-Distance Steady Run",
        2: "Low-Intensity Run",
        3: "Long Tempo Run"
    }
    run_type = cluster_labels[label]

    # Insert the new run with the cluster label into the clustering_labels table
    row_to_insert = {
        "id": latest_run.iloc[0]["id"],
        "start_date": latest_run.iloc[0]["start_date"],
        "distance": latest_run.iloc[0]["distance"],
        "moving_time": latest_run.iloc[0]["moving_time"],
        "average_heartrate": latest_run.iloc[0]["average_heartrate"],
        "run_type": run_type
    }
    errors = client.insert_rows_json(table_id, [row_to_insert])
    if errors:
        return f"Errors occurred: {errors}", 500

    return "Latest run processed successfully", 200