from google.cloud import bigquery, storage
import functions_framework
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import joblib
import os

@functions_framework.http  # Change from cloud_event to http
def train_kmeans(request):
    # Initialize BigQuery and GCS clients
    bq_client = bigquery.Client(project="strava-etl")
    storage_client = storage.Client(project="strava-etl")

    # Read preprocessed data
    query = """
        SELECT distance, moving_time, suffer_score
        FROM `strava-etl.strava_data.clustering_data`
    """
    df = bq_client.query(query).to_dataframe()

    # Check if data is sufficient
    if df.empty:
        print("No data available for training.")
        return "No data available for training.", 200

    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df)

    # Train K-Means model
    kmeans = KMeans(n_clusters=4, random_state=42)
    kmeans.fit(X_scaled)

    # Save scaler and model to GCS
    bucket_name = 'strava-models'
    bucket = storage_client.bucket(bucket_name)

    # Save scaler
    scaler_blob = bucket.blob('models/scaler.joblib')
    scaler_path = '/tmp/scaler.joblib'
    joblib.dump(scaler, scaler_path)
    scaler_blob.upload_from_filename(scaler_path)

    # Save model
    model_blob = bucket.blob('models/kmeans_model.joblib')
    model_path = '/tmp/kmeans_model.joblib'
    joblib.dump(kmeans, model_path)
    model_blob.upload_from_filename(model_path)

    print("Model and scaler saved to GCS.")
    return "Model training complete and saved to GCS.", 200
