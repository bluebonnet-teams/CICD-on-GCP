import io
import os
from google.cloud import storage
import functions_framework
from datetime import datetime
import pandas as pd
from cloudevents.http import CloudEvent

_ENV = os.environ.get("ENV", "Specified environment variable is not set.")

@functions_framework.cloud_event
def intro_func(cloud_event: CloudEvent):
    """This function is triggered by a change in a storage bucket.

    Args:
        cloud_event: The CloudEvent that triggered this function.
    Returns:
        The event ID, event type, bucket, name, metageneration, and timeCreated.
    """
    data = cloud_event.data

    event_id = cloud_event["id"]
    event_type = cloud_event["type"]

    print("Hi")

    bucket = data["bucket"]
    print(bucket)
    name = data["name"]
    print(name)
    metageneration = data["metageneration"]
    timeCreated = data["timeCreated"]
    updated = data["updated"]

    env_bucket_name = f"csv-data-{_ENV}-bucket"
    clean_bucket_name = f"clean-data-{_ENV}-bucket"
    trigger_file_name = "done_with_csv.txt"

    if bucket == env_bucket_name and name.endswith(trigger_file_name):
        process_trigger(bucket=bucket, clean_bucket=clean_bucket_name, file_name=name)
        return 0
    else:
        return 1


def list_blobs(bucket_name, prefix):
    """Lists all the blobs in the bucket."""
    # bucket_name = "your-bucket-name"

    storage_client = storage.Client()

    # Note: Client.list_blobs requires at least package version 1.17.0.
    blobs = storage_client.list_blobs(bucket_name, prefix=prefix)

    return blobs

def process_trigger(bucket, clean_bucket, file_name):
    delim = "/"
    dir_to_process = delim.join(file_name.split(delim)[:-1])
    print(f"Reading files from this dir: {dir_to_process}")

    blobs = list_blobs(bucket_name=bucket, prefix=dir_to_process)

    paths = []
    for file in blobs:
        full_path = f"gs://{file.bucket.name}/{file.name}"
        paths.append(full_path)

    df = pd.concat(map(pd.read_csv, paths))

    df['timestamp'] = datetime.now()

    df.to_parquet(f"gs://{clean_bucket}/clean_data.parquet")