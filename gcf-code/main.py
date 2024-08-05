# Import libraries you need
import io
import os
from google.cloud import storage
import functions_framework
from datetime import datetime
import pandas as pd
from cloudevents.http import CloudEvent

# Retrieve the Environment Variable that determines what environment we are in
_ENV = os.environ.get("ENV", "Specified environment variable is not set.")

# This decorator allows us to trigger this code via a CloudEvent object
@functions_framework.cloud_event
def intro_func(cloud_event: CloudEvent):
    """This function is triggered by a change in a storage bucket.
    Args:
        cloud_event: The CloudEvent that triggered this function.
    Returns:
        0: if a trigger file is processed successfully
        1: if a non-trigger file is received
    """

    # Get the underlying data from the event
    data = cloud_event.data

    # Get the bucket name
    bucket = data["bucket"]
    # Get the full path of the object that triggered the function
    name = data["name"]

    # Based on the environment, define the bucket name we need to validate against
    # to ensure that the file is coming from the right place
    env_bucket_name = f"csv-data-{_ENV}-bucket"
    # Define the bucket name where we will write
    clean_bucket_name = f"clean-data-{_ENV}-bucket"
    # Define the trigger file name that we are expecting
    trigger_file_name = "done_with_csv.txt"

    # Check that the bucket is correct and only look for the trigger file
    if bucket == env_bucket_name and name.endswith(trigger_file_name):
        # If there is a match, process the file
        process_trigger(bucket=bucket, clean_bucket=clean_bucket_name, file_name=name)
        return 0
    # If there is no match, do not process the file
    else:
        return 1


def list_blobs(bucket_name, prefix):
    """Lists all the blobs in the bucket with a given prefix and that are only .csv files"""
    # Define a client to interact with the storage buckets
    storage_client = storage.Client()

    # List blobs for the bucket with a given prefix
    blobs = storage_client.list_blobs(bucket_name, prefix=prefix)

    # Filter out to only .csv files
    final_blobs = []
    for blob in blobs:
        if blob.name.endswith(".csv"):
            final_blobs.append(blob)

    # Return the final list
    return final_blobs


# Define the function to take in a bucket, clean bucket to write, and a trigger file name
def process_trigger(bucket, clean_bucket, file_name):
    # Take the trigger file name and extract the parent directory of the file
    # This is our directory where we are going to read from
    delim = "/"
    dir_to_process = delim.join(file_name.split(delim)[:-1])
    print(f"Reading files from this dir: {dir_to_process}")

    # Get the list of .csv files to process
    blobs = list_blobs(bucket_name=bucket, prefix=dir_to_process)

    # Build the full path needed by Pandas to read the file
    paths = []
    for file in blobs:
        full_path = f"gs://{file.bucket.name}/{file.name}"
        paths.append(full_path)

    # For each file, read it via read_csv and concatenate them into one Dataframe
    df = pd.concat(map(pd.read_csv, paths))

    # Add a timestamp of the time of processing
    df['timestamp'] = datetime.now()

    # Save the data in the clean bucket
    df.to_parquet(f"gs://{clean_bucket}/clean_data.parquet")

    # Return 0 if all is a success
    return 0