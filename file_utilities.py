import boto3
import botocore
import configparser
from loguru import logger

config = configparser.ConfigParser()
config.read('config.ini')

BUCKET_NAME = 'reflector-bucket'

s3 = boto3.client('s3',
                  aws_access_key_id=config["DEFAULT"]["AWS_ACCESS_KEY"],
                  aws_secret_access_key=config["DEFAULT"]["AWS_SECRET_KEY"])

def upload_files(files_to_upload):
    """
    Upload a list of files to the configured S3 bucket
    :param files_to_upload:
    :return:
    """
    for KEY in files_to_upload:
        logger.info("Uploading file " + KEY)
        try:
            s3.upload_file(KEY, BUCKET_NAME, KEY)
        except botocore.exceptions.ClientError as e:
            print(e.response)


def download_files(files_to_download):
    """
    Download a list of files from the configured S3 bucket
    :param files_to_download:
    :return:
    """
    for KEY in files_to_download:
        logger.info("Downloading file " + KEY)
        try:
            s3.download_file(BUCKET_NAME, KEY, KEY)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                print("The object does not exist.")
            else:
                raise


if __name__ == "__main__":
    import sys
    if sys.argv[1] == "download":
        download_files([sys.argv[2]])
    elif sys.argv[1] == "upload":
        upload_files([sys.argv[2]])
