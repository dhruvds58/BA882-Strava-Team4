from prefect import flow

if __name__ == "__main__":
    flow.from_source(
        source="https://github.com/dhruvds58/BA882-Strava-Team4.git",
        entrypoint="prefect/flows/etl_flow.py:etl_flow",
    ).deploy(
        name="strava-etl-flow",
        work_pool_name="strava-etl-pool",
        job_variables={
            "env": {"PROJECT_ID": "strava-etl"},
            "pip_packages": ["google-cloud-storage", "google-cloud-bigquery", "pandas"]
        },
        tags=["prod"],
        description="ETL flow for processing Strava activity data",
        version="1.0.2",
    )