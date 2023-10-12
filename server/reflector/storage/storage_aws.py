import aioboto3
from reflector.logger import logger
from reflector.storage.base import FileResult, Storage


class AwsStorage(Storage):
    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_bucket_name: str,
        aws_region: str,
    ):
        if not aws_access_key_id:
            raise ValueError("Storage `aws_storage` require `aws_access_key_id`")
        if not aws_secret_access_key:
            raise ValueError("Storage `aws_storage` require `aws_secret_access_key`")
        if not aws_bucket_name:
            raise ValueError("Storage `aws_storage` require `aws_bucket_name`")
        if not aws_region:
            raise ValueError("Storage `aws_storage` require `aws_region`")

        super().__init__()
        self.aws_bucket_name = aws_bucket_name
        self.aws_folder = ""
        if "/" in aws_bucket_name:
            self.aws_bucket_name, self.aws_folder = aws_bucket_name.split("/", 1)
        self.session = aioboto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )
        self.base_url = f"https://{aws_bucket_name}.s3.amazonaws.com/"

    async def _put_file(self, filename: str, data: bytes) -> FileResult:
        bucket = self.aws_bucket_name
        folder = self.aws_folder
        logger.info(f"Uploading {filename} to S3 {bucket}/{folder}")
        s3filename = f"{folder}/{filename}" if folder else filename
        async with self.session.client("s3") as client:
            await client.put_object(
                Bucket=bucket,
                Key=s3filename,
                Body=data,
            )

            presigned_url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": s3filename},
                ExpiresIn=3600,
            )

            return FileResult(
                filename=filename,
                url=presigned_url,
            )

    async def _delete_file(self, filename: str):
        bucket = self.aws_bucket_name
        folder = self.aws_folder
        logger.info(f"Deleting {filename} from S3 {bucket}/{folder}")
        s3filename = f"{folder}/{filename}" if folder else filename
        async with self.session.client("s3") as client:
            await client.delete_object(Bucket=bucket, Key=s3filename)


Storage.register("aws", AwsStorage)
