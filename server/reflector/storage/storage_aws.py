from typing import BinaryIO, Union

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError

from reflector.logger import logger
from reflector.storage.base import FileResult, Storage


class AwsStorage(Storage):
    """AWS S3 storage with bucket override for multi-platform recording architecture.
    Master credentials access all buckets via optional bucket parameter in operations."""

    def __init__(
        self,
        aws_bucket_name: str,
        aws_region: str,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_role_arn: str | None = None,
    ):
        if not aws_bucket_name:
            raise ValueError("Storage `aws_storage` require `aws_bucket_name`")
        if not aws_region:
            raise ValueError("Storage `aws_storage` require `aws_region`")
        if not aws_access_key_id and not aws_role_arn:
            raise ValueError(
                "Storage `aws_storage` require either `aws_access_key_id` or `aws_role_arn`"
            )

        super().__init__()
        self._bucket_name = aws_bucket_name
        self._region = aws_region
        self._access_key_id = aws_access_key_id
        self._secret_access_key = aws_secret_access_key
        self._role_arn = aws_role_arn

        self.aws_folder = ""
        if "/" in aws_bucket_name:
            self._bucket_name, self.aws_folder = aws_bucket_name.split("/", 1)
        self.boto_config = Config(retries={"max_attempts": 3, "mode": "adaptive"})
        self.session = aioboto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )
        self.base_url = f"https://{self._bucket_name}.s3.amazonaws.com/"

    # Implement credential properties
    @property
    def bucket_name(self) -> str:
        return self._bucket_name

    @property
    def region(self) -> str:
        return self._region

    @property
    def access_key_id(self) -> str | None:
        return self._access_key_id

    @property
    def secret_access_key(self) -> str | None:
        return self._secret_access_key

    @property
    def role_arn(self) -> str | None:
        return self._role_arn

    @property
    def key_credentials(self) -> tuple[str, str]:
        """Get (access_key_id, secret_access_key) for key-based auth."""
        if self._role_arn:
            raise ValueError(
                "Storage uses IAM role authentication. "
                "Use role_credential property instead of key_credentials."
            )
        if not self._access_key_id or not self._secret_access_key:
            raise ValueError("Storage access key credentials not configured")
        return (self._access_key_id, self._secret_access_key)

    @property
    def role_credential(self) -> str:
        """Get IAM role ARN for role-based auth."""
        if self._access_key_id or self._secret_access_key:
            raise ValueError(
                "Storage uses access key authentication. "
                "Use key_credentials property instead of role_credential."
            )
        if not self._role_arn:
            raise ValueError("Storage IAM role ARN not configured")
        return self._role_arn

    async def _put_file(
        self, filename: str, data: Union[bytes, BinaryIO], bucket: str | None = None
    ) -> FileResult:
        actual_bucket = bucket or self._bucket_name
        folder = self.aws_folder
        s3filename = f"{folder}/{filename}" if folder else filename
        logger.info(f"Uploading {filename} to S3 {actual_bucket}/{folder}")

        try:
            async with self.session.client("s3", config=self.boto_config) as client:
                if isinstance(data, bytes):
                    await client.put_object(
                        Bucket=actual_bucket, Key=s3filename, Body=data
                    )
                else:
                    # boto3 reads file-like object in chunks
                    # avoids creating extra memory copy vs bytes.getvalue() approach
                    await client.upload_fileobj(
                        data, Bucket=actual_bucket, Key=s3filename
                    )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("AccessDenied", "NoSuchBucket"):
                bucket_context = (
                    f"overridden bucket '{actual_bucket}'"
                    if bucket
                    else f"default bucket '{actual_bucket}'"
                )
                raise Exception(
                    f"S3 upload failed for {bucket_context}: {error_code}. "
                    f"Check TRANSCRIPT_STORAGE_AWS_* credentials have permission."
                ) from e
            raise

        url = await self._get_file_url(filename, bucket=bucket)
        return FileResult(filename=filename, url=url)

    async def _get_file_url(
        self,
        filename: str,
        operation: str = "get_object",
        expires_in: int = 3600,
        bucket: str | None = None,
    ) -> str:
        actual_bucket = bucket or self._bucket_name
        folder = self.aws_folder
        s3filename = f"{folder}/{filename}" if folder else filename
        async with self.session.client("s3", config=self.boto_config) as client:
            presigned_url = await client.generate_presigned_url(
                operation,
                Params={"Bucket": actual_bucket, "Key": s3filename},
                ExpiresIn=expires_in,
            )

            return presigned_url

    async def _delete_file(self, filename: str, bucket: str | None = None):
        actual_bucket = bucket or self._bucket_name
        folder = self.aws_folder
        logger.info(f"Deleting {filename} from S3 {actual_bucket}/{folder}")
        s3filename = f"{folder}/{filename}" if folder else filename
        try:
            async with self.session.client("s3", config=self.boto_config) as client:
                await client.delete_object(Bucket=actual_bucket, Key=s3filename)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("AccessDenied", "NoSuchBucket"):
                bucket_context = (
                    f"overridden bucket '{actual_bucket}'"
                    if bucket
                    else f"default bucket '{actual_bucket}'"
                )
                raise Exception(
                    f"S3 delete failed for {bucket_context}: {error_code}. "
                    f"Check TRANSCRIPT_STORAGE_AWS_* credentials have permission."
                ) from e
            raise

    async def _get_file(self, filename: str, bucket: str | None = None):
        actual_bucket = bucket or self._bucket_name
        folder = self.aws_folder
        logger.info(f"Downloading {filename} from S3 {actual_bucket}/{folder}")
        s3filename = f"{folder}/{filename}" if folder else filename
        try:
            async with self.session.client("s3", config=self.boto_config) as client:
                response = await client.get_object(Bucket=actual_bucket, Key=s3filename)
                return await response["Body"].read()
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("AccessDenied", "NoSuchBucket"):
                bucket_context = (
                    f"overridden bucket '{actual_bucket}'"
                    if bucket
                    else f"default bucket '{actual_bucket}'"
                )
                raise Exception(
                    f"S3 download failed for {bucket_context}: {error_code}. "
                    f"Check TRANSCRIPT_STORAGE_AWS_* credentials have permission."
                ) from e
            raise

    async def _list_objects(
        self, prefix: str = "", bucket: str | None = None
    ) -> list[str]:
        actual_bucket = bucket or self._bucket_name
        folder = self.aws_folder
        # Combine folder and prefix
        s3prefix = f"{folder}/{prefix}" if folder else prefix
        logger.info(f"Listing objects from S3 {actual_bucket} with prefix '{s3prefix}'")

        keys = []
        try:
            async with self.session.client("s3", config=self.boto_config) as client:
                paginator = client.get_paginator("list_objects_v2")
                async for page in paginator.paginate(
                    Bucket=actual_bucket, Prefix=s3prefix
                ):
                    if "Contents" in page:
                        for obj in page["Contents"]:
                            # Strip folder prefix from keys if present
                            key = obj["Key"]
                            if folder and key.startswith(f"{folder}/"):
                                key = key[len(folder) + 1 :]
                            keys.append(key)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("AccessDenied", "NoSuchBucket"):
                bucket_context = (
                    f"overridden bucket '{actual_bucket}'"
                    if bucket
                    else f"default bucket '{actual_bucket}'"
                )
                raise Exception(
                    f"S3 list_objects failed for {bucket_context}: {error_code}. "
                    f"Check TRANSCRIPT_STORAGE_AWS_* credentials have permission."
                ) from e
            raise

        return keys

    async def _stream_to_fileobj(
        self, filename: str, fileobj: BinaryIO, bucket: str | None = None
    ):
        """Stream file from S3 directly to file object without loading into memory."""
        actual_bucket = bucket or self._bucket_name
        folder = self.aws_folder
        logger.info(f"Streaming {filename} from S3 {actual_bucket}/{folder}")
        s3filename = f"{folder}/{filename}" if folder else filename
        try:
            async with self.session.client("s3", config=self.boto_config) as client:
                response = await client.get_object(Bucket=actual_bucket, Key=s3filename)
                # Stream response body in chunks to file object
                # This avoids loading entire file into memory
                body = response["Body"]
                try:
                    while True:
                        chunk = await body.read(1024 * 1024)  # 1MB chunks
                        if not chunk:
                            break
                        fileobj.write(chunk)
                    fileobj.flush()
                finally:
                    # Ensure S3 response body is closed even if write fails
                    if hasattr(body, "close"):
                        body.close()
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("AccessDenied", "NoSuchBucket"):
                bucket_context = (
                    f"overridden bucket '{actual_bucket}'"
                    if bucket
                    else f"default bucket '{actual_bucket}'"
                )
                raise Exception(
                    f"S3 stream failed for {bucket_context}: {error_code}. "
                    f"Check TRANSCRIPT_STORAGE_AWS_* credentials have permission."
                ) from e
            raise


Storage.register("aws", AwsStorage)
