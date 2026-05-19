"""
Smart Notes Vault - Configuration
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv(override=True)

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-in-production-use-secrets-manager')

    # Database - AWS RDS (MySQL/PostgreSQL)
    # Format: mysql+pymysql://user:pass@host:port/dbname
    #         postgresql://user:pass@host:port/dbname
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///dev_vault.db'   # SQLite fallback for local dev only
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # Session
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # AWS
    AWS_REGION            = os.environ.get('AWS_REGION', 'ap-south-1')
    AWS_S3_BUCKET         = os.environ.get('AWS_S3_BUCKET', 'smart-notes-vault-bucket')
    # On EC2 with IAM Role, boto3 picks up credentials automatically.
    # For local dev, set these:
    AWS_ACCESS_KEY_ID     = os.environ.get('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')

    # CloudWatch
    CLOUDWATCH_LOG_GROUP  = os.environ.get('CLOUDWATCH_LOG_GROUP', '/smart-notes-vault/app')
    CLOUDWATCH_LOG_STREAM = os.environ.get('CLOUDWATCH_LOG_STREAM', 'application')

    # Email (Brevo SMTP or AWS SES SMTP)
    MAIL_SERVER   = os.environ.get('MAIL_SERVER', 'smtp-relay.brevo.com')
    MAIL_PORT     = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS  = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_FROM     = os.environ.get('MAIL_FROM', 'noreply@smartnotesvault.com')

    # OTP settings
    OTP_EXPIRY_MINUTES = 10
    OTP_MAX_ATTEMPTS   = 5

    # Fernet encryption key (32-byte url-safe base64 encoded)
    # Generate with: from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())
    FERNET_KEY = os.environ.get('FERNET_KEY', '')
