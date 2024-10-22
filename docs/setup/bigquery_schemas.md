# BigQuery Schema Definitions

This guide details the schema definitions for the BigQuery tables used in the Strava ETL pipeline.

## Activities Table

```json
{
  "fields": [
    {"name": "id", "type": "INTEGER", "mode": "REQUIRED", "description": "Strava activity ID"},
    {"name": "resource_state", "type": "INTEGER"},
    {"name": "name", "type": "STRING"},
    {"name": "distance", "type": "FLOAT"},
    {"name": "moving_time", "type": "INTEGER"},
    {"name": "elapsed_time", "type": "INTEGER"},
    {"name": "total_elevation_gain", "type": "FLOAT"},
    {"name": "type", "type": "STRING"},
    {"name": "sport_type", "type": "STRING"},
    {"name": "workout_type", "type": "INTEGER"},
    {"name": "start_date", "type": "TIMESTAMP"},
    {"name": "start_date_local", "type": "TIMESTAMP"},
    {"name": "timezone", "type": "STRING"},
    {"name": "start_latlng", "type": "STRING"},
    {"name": "end_latlng", "type": "STRING"},
    {"name": "achievement_count", "type": "INTEGER"},
    {"name": "kudos_count", "type": "INTEGER"},
    {"name": "comment_count", "type": "INTEGER"},
    {"name": "athlete_count", "type": "INTEGER"},
    {"name": "photo_count", "type": "INTEGER"},
    {"name": "trainer", "type": "BOOLEAN"},
    {"name": "commute", "type": "BOOLEAN"},
    {"name": "manual", "type": "BOOLEAN"},
    {"name": "private", "type": "BOOLEAN"},
    {"name": "flagged", "type": "BOOLEAN"},
    {"name": "gear_id", "type": "STRING"},
    {"name": "average_speed", "type": "FLOAT"},
    {"name": "max_speed", "type": "FLOAT"},
    {"name": "average_cadence", "type": "FLOAT"},
    {"name": "average_watts", "type": "FLOAT"},
    {"name": "max_watts", "type": "INTEGER"},
    {"name": "weighted_average_watts", "type": "INTEGER"},
    {"name": "kilojoules", "type": "FLOAT"},
    {"name": "device_watts", "type": "BOOLEAN"},
    {"name": "has_heartrate", "type": "BOOLEAN"},
    {"name": "average_heartrate", "type": "FLOAT"},
    {"name": "max_heartrate", "type": "FLOAT"},
    {"name": "elev_high", "type": "FLOAT"},
    {"name": "elev_low", "type": "FLOAT"},
    {"name": "upload_id", "type": "INTEGER"},
    {"name": "external_id", "type": "STRING"},
    {"name": "pr_count", "type": "INTEGER"},
    {"name": "total_photo_count", "type": "INTEGER"},
    {"name": "suffer_score", "type": "FLOAT"},
    {"name": "athlete_id", "type": "INTEGER", "description": "Strava athlete ID"},
    {"name": "day_of_week", "type": "STRING"},
    {"name": "hour", "type": "INTEGER"},
    {"name": "month", "type": "STRING"},
    {"name": "elevation_change", "type": "FLOAT"}
  ]
}
```

## Laps Table

```json
{
  "fields": [
    {"name": "id", "type": "INTEGER", "mode": "REQUIRED", "description": "Lap ID"},
    {"name": "resource_state", "type": "INTEGER"},
    {"name": "name", "type": "STRING"},
    {"name": "activity_id", "type": "INTEGER"},
    {"name": "athlete_id", "type": "INTEGER"},
    {"name": "elapsed_time", "type": "INTEGER"},
    {"name": "moving_time", "type": "INTEGER"},
    {"name": "start_date", "type": "TIMESTAMP"},
    {"name": "start_date_local", "type": "TIMESTAMP"},
    {"name": "distance", "type": "FLOAT"},
    {"name": "start_index", "type": "INTEGER"},
    {"name": "end_index", "type": "INTEGER"},
    {"name": "total_elevation_gain", "type": "FLOAT"},
    {"name": "average_speed", "type": "FLOAT"},
    {"name": "max_speed", "type": "FLOAT"},
    {"name": "average_cadence", "type": "FLOAT"},
    {"name": "device_watts", "type": "BOOLEAN"},
    {"name": "average_watts", "type": "FLOAT"},
    {"name": "lap_index", "type": "INTEGER"},
    {"name": "average_heartrate", "type": "FLOAT"},
    {"name": "max_heartrate", "type": "FLOAT"},
    {"name": "pace_zone", "type": "INTEGER"}
  ]
}
```

## Creating Tables

```bash
# Create activities table
bq mk \
  --table \
  strava-etl:strava_data.activities \
  schemas/activities_schema.json

# Create laps table
bq mk \
  --table \
  strava-etl:strava_data.laps \
  schemas/laps_schema.json
```

## Sample Queries

```sql
-- Get activity summary by type
SELECT 
  type,
  COUNT(*) as activity_count,
  AVG(distance) as avg_distance,
  AVG(moving_time) as avg_moving_time
FROM `strava-etl.strava_data.activities`
GROUP BY type
ORDER BY activity_count DESC;

-- Get athlete's weekly stats
SELECT 
  athlete_id,
  day_of_week,
  COUNT(*) as activities,
  SUM(distance) as total_distance,
  AVG(average_heartrate) as avg_heartrate
FROM `strava-etl.strava_data.activities`
GROUP BY athlete_id, day_of_week
ORDER BY athlete_id, activities DESC;
```