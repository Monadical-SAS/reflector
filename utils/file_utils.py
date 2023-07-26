"""
Utility file for file handling related functions, including file downloads and
uploads to cloud storage
"""

import sys

import boto3
import botocore

from .log_utils import LOGGER
from .run_utils import CONFIG

BUCKET_NAME = CONFIG["AWS"]["BUCKET_NAME"]

s3 = boto3.client('s3',
                  aws_access_key_id=CONFIG["AWS"]["AWS_ACCESS_KEY"],
                  aws_secret_access_key=CONFIG["AWS"]["AWS_SECRET_KEY"])


def upload_files(files_to_upload):
    """
    Upload a list of files to the configured S3 bucket
    :param files_to_upload: List of files to upload
    :return: None
    """
    for key in files_to_upload:
        LOGGER.info("Uploading file " + key)
        try:
            s3.upload_file(key, BUCKET_NAME, key)
        except botocore.exceptions.ClientError as exception:
            print(exception.response)


def download_files(files_to_download):
    """
    Download a list of files from the configured S3 bucket
    :param files_to_download: List of files to download
    :return: None
    """
    for key in files_to_download:
        LOGGER.info("Downloading file " + key)
        try:
            s3.download_file(BUCKET_NAME, key, key)
        except botocore.exceptions.ClientError as exception:
            if exception.response['Error']['Code'] == "404":
                print("The object does not exist.")
            else:
                raise


if __name__ == "__main__":
    if sys.argv[1] == "download":
        download_files([sys.argv[2]])
    elif sys.argv[1] == "upload":
        upload_files([sys.argv[2]])
