# Module Imports
import os
import io
import boto3
from botocore.exceptions import ClientError
from config import settings

# Setup client
s3 = boto3.client(
    "s3",
    endpoint_url=settings.STORAGE_BUCKET_ENDPOINT,
    aws_access_key_id=settings.STORAGE_BUCKET_ACCESS_KEY,
    aws_secret_access_key=settings.STORAGE_BUCKET_SECRET_KEY,
    region_name=settings.STORAGE_BUCKET_REGION_NAME)
bucket_name: str = settings.STORAGE_BUCKET_NAME

# Create bucket
def create_bucket():
    try:
        s3.head_bucket(Bucket=bucket_name)
    except ClientError:
        s3.create_bucket(Bucket=bucket_name)

# Upload file
def upload_file_to_bucket(file_content, file_name):
    try:
        s3.upload_fileobj(Fileobj=file_content, 
                          Bucket=bucket_name, 
                          Key=file_name, 
                          ExtraArgs={"ContentType": "image/png", 
                                     "CacheControl": f"max-age={settings.STORAGE_BUCKET_CACHE_TIMEOUT}"})
        return True
    except ClientError:
        return False

# Delete file
def delete_file_from_bucket(file_name):
    try:
        s3.delete_object(Bucket=bucket_name, 
                         Key=file_name)
        return True
    except ClientError:
        return False
