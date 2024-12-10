from google.cloud import bigquery
from google.api_core.exceptions import NotFound
import functions_framework

@functions_framework.http
def preprocess_data(request):
    # Explicitly set the project ID
    client = bigquery.Client(project="strava-etl")

    # Define the table ID
    table_id = 'strava-etl.strava_data.clustering_data'

    # Check if the table exists, and create it if it doesn't
    create_table_if_not_exists(client, table_id)

    # Query to get data from activities table
    query = """
        SELECT *
        FROM `strava-etl.strava_data.activities`
    """
    activities = client.query(query).to_dataframe()

    # Remove empty columns
    activities = activities.dropna(axis=1, how='all')

    # Filter out runs with distance < 100
    activities = activities[activities['distance'] > 100]

    # Select relevant columns
    clustering_data = activities[['id', 'distance', 'moving_time', 'suffer_score']]

    # Write to BigQuery table
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    job = client.load_table_from_dataframe(clustering_data, table_id, job_config=job_config)
    job.result()  # Wait for the job to complete

    print("Preprocessed data written to clustering_data table.")
    return 'Data processing complete', 200

def create_table_if_not_exists(client, table_id):
    """Creates the BigQuery table if it doesn't exist."""
    try:
        client.get_table(table_id)  # Check if table exists
        print(f"Table {table_id} already exists.")
    except NotFound:
        # Define the schema
        schema = [
            bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("distance", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("moving_time", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("suffer_score", "FLOAT", mode="NULLABLE"),
        ]
        # Create the table with the specified schema
        table = bigquery.Table(table_id, schema=schema)
        client.create_table(table)  # Make the API request to create the table
        print(f"Created table {table_id}.")
