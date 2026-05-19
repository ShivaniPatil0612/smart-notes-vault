"""
Smart Notes Vault - AWS S3 Handler
Handles encrypted note upload / download / delete in S3.
"""

import boto3
import logging
from botocore.exceptions import ClientError, BotoCoreError
from flask import current_app

logger = logging.getLogger(__name__)


def _get_s3_client():
    """Return a boto3 S3 client. On EC2, IAM role credentials are used automatically."""
    cfg = current_app.config
    kwargs = {'region_name': cfg['AWS_REGION']}
    # Only add explicit keys if provided (for local dev)
    if cfg.get('AWS_ACCESS_KEY_ID') and cfg.get('AWS_SECRET_ACCESS_KEY'):
        kwargs['aws_access_key_id']     = cfg['AWS_ACCESS_KEY_ID']
        kwargs['aws_secret_access_key'] = cfg['AWS_SECRET_ACCESS_KEY']
    return boto3.client('s3', **kwargs)


def upload_encrypted_note(s3_key: str, ciphertext: bytes) -> bool:
    """Upload encrypted bytes to S3 under s3_key."""
    try:
        client = _get_s3_client()
        bucket = current_app.config['AWS_S3_BUCKET']
        client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=ciphertext,
            ContentType='application/octet-stream',
            ServerSideEncryption='AES256',   # S3-managed SSE as extra layer
        )
        logger.info(f"Uploaded note to S3: {s3_key}")
        return True
    except (ClientError, BotoCoreError) as e:
        logger.error(f"S3 upload failed for {s3_key}: {e}")
        return False


def download_encrypted_note(s3_key: str) -> bytes | None:
    """Download encrypted bytes from S3."""
    try:
        client = _get_s3_client()
        bucket = current_app.config['AWS_S3_BUCKET']
        response = client.get_object(Bucket=bucket, Key=s3_key)
        data = response['Body'].read()
        logger.info(f"Downloaded note from S3: {s3_key}")
        return data
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.warning(f"S3 key not found: {s3_key}")
        else:
            logger.error(f"S3 download failed for {s3_key}: {e}")
        return None
    except BotoCoreError as e:
        logger.error(f"S3 download error for {s3_key}: {e}")
        return None


def delete_encrypted_note(s3_key: str) -> bool:
    """Delete an object from S3."""
    try:
        client = _get_s3_client()
        bucket = current_app.config['AWS_S3_BUCKET']
        client.delete_object(Bucket=bucket, Key=s3_key)
        logger.info(f"Deleted note from S3: {s3_key}")
        return True
    except (ClientError, BotoCoreError) as e:
        logger.error(f"S3 delete failed for {s3_key}: {e}")
        return False


def note_exists(s3_key: str) -> bool:
    """Check whether an S3 object exists."""
    try:
        client = _get_s3_client()
        bucket = current_app.config['AWS_S3_BUCKET']
        client.head_object(Bucket=bucket, Key=s3_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] in ('404', 'NoSuchKey'):
            return False
        logger.error(f"S3 head_object error: {e}")
        return False
