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
            "pip_packages": [
                "prefect==3.0.10",
                "prefect-gcp==0.6.1",
                "google-cloud-storage==2.18.2",
                "google-cloud-bigquery==3.26.0",
                "pandas==2.2.3",
                "pyarrow==17.0.0"
            ]
        },
        tags=["prod"],
        description="ETL flow for processing Strava activity data",
        version="1.0.3",
    )


# from prefect import flow

# if __name__ == "__main__":
#     flow.from_source(
#         source="https://github.com/dhruvds58/BA882-Strava-Team4.git",
#         entrypoint="prefect/flows/etl_flow.py:etl_flow",
#     ).deploy(
#         name="strava-etl-flow",
#         work_pool_name="strava-etl-pool",
#         job_variables={
#             "env": {"PROJECT_ID": "strava-etl"},
#             "pip_packages": ["google-cloud-storage", "google-cloud-bigquery", "pandas", "pyarrow"]
#         },
#         tags=["prod"],
#         description="ETL flow for processing Strava activity data",
#         version="1.0.2",
#     )