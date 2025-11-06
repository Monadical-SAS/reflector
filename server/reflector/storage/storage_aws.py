from typing import BinaryIO, Union

import aioboto3
from botocore.config import Config

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
        self.boto_config = Config(retries={"max_attempts": 3, "mode": "adaptive"})
        self.session = aioboto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )
        self.base_url = f"https://{aws_bucket_name}.s3.amazonaws.com/"

    async def _put_file(
        self, filename: str, data: Union[bytes, BinaryIO]
    ) -> FileResult:
        bucket = self.aws_bucket_name
        folder = self.aws_folder
        s3filename = f"{folder}/{filename}" if folder else filename
        logger.info(f"Uploading {filename} to S3 {bucket}/{folder}")

        async with self.session.client("s3", config=self.boto_config) as client:
            if isinstance(data, bytes):
                await client.put_object(Bucket=bucket, Key=s3filename, Body=data)
            else:
                # boto3 reads file-like object in chunks
                # avoids creating extra memory copy vs bytes.getvalue() approach
                await client.upload_fileobj(data, Bucket=bucket, Key=s3filename)

        url = await self._get_file_url(filename)
        return FileResult(filename=filename, url=url)

    async def _get_file_url(
        self, filename: str, operation: str = "get_object", expires_in: int = 3600
    ) -> str:
        bucket = self.aws_bucket_name
        folder = self.aws_folder
        s3filename = f"{folder}/{filename}" if folder else filename
        async with self.session.client("s3", config=self.boto_config) as client:
            presigned_url = await client.generate_presigned_url(
                operation,
                Params={"Bucket": bucket, "Key": s3filename},
                ExpiresIn=expires_in,
            )

            return presigned_url

    async def _delete_file(self, filename: str):
        bucket = self.aws_bucket_name
        folder = self.aws_folder
        logger.info(f"Deleting {filename} from S3 {bucket}/{folder}")
        s3filename = f"{folder}/{filename}" if folder else filename
        async with self.session.client("s3", config=self.boto_config) as client:
            await client.delete_object(Bucket=bucket, Key=s3filename)

    async def _get_file(self, filename: str):
        bucket = self.aws_bucket_name
        folder = self.aws_folder
        logger.info(f"Downloading {filename} from S3 {bucket}/{folder}")
        s3filename = f"{folder}/{filename}" if folder else filename
        async with self.session.client("s3", config=self.boto_config) as client:
            response = await client.get_object(Bucket=bucket, Key=s3filename)
            return await response["Body"].read()


Storage.register("aws", AwsStorage)
