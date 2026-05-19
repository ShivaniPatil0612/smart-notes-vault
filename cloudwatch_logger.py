"""
Smart Notes Vault - AWS CloudWatch Logging
Sends structured log events for security monitoring.
"""

import boto3
import json
import time
import logging
from datetime import datetime, timezone
from botocore.exceptions import ClientError, BotoCoreError
from flask import current_app, request

logger = logging.getLogger(__name__)

_sequence_token = None   # CloudWatch requires a sequence token between PutLogEvents calls


def _get_logs_client():
    cfg = current_app.config
    kwargs = {'region_name': cfg['AWS_REGION']}
    if cfg.get('AWS_ACCESS_KEY_ID') and cfg.get('AWS_SECRET_ACCESS_KEY'):
        kwargs['aws_access_key_id']     = cfg['AWS_ACCESS_KEY_ID']
        kwargs['aws_secret_access_key'] = cfg['AWS_SECRET_ACCESS_KEY']
    return boto3.client('logs', **kwargs)


def _put_log(event_type: str, details: dict):
    """Send a single structured log event to CloudWatch."""
    global _sequence_token
    try:
        client     = _get_logs_client()
        log_group  = current_app.config['CLOUDWATCH_LOG_GROUP']
        log_stream = current_app.config['CLOUDWATCH_LOG_STREAM']

        event = {
            'event_type': event_type,
            'timestamp':  datetime.now(timezone.utc).isoformat(),
            'ip':         request.remote_addr if request else 'unknown',
            **details
        }

        kwargs = {
            'logGroupName':  log_group,
            'logStreamName': log_stream,
            'logEvents': [{
                'timestamp': int(time.time() * 1000),
                'message':   json.dumps(event)
            }]
        }

        # Send to CloudWatch (sequenceToken is no longer required by AWS)
        client.put_log_events(**kwargs)

    except (ClientError, BotoCoreError) as e:
        # Never crash the app because of logging failure
        logger.warning(f"CloudWatch log failed: {e}")
    except Exception as e:
        logger.warning(f"Unexpected CloudWatch error: {e}")


# ── Public helpers ────────────────────────────────────────────────────────────

def log_login_success(user_email: str):
    _put_log('LOGIN_SUCCESS', {'email': user_email})

def log_login_failure(user_email: str, reason: str = ''):
    _put_log('LOGIN_FAILURE', {'email': user_email, 'reason': reason})

def log_otp_failure(user_email: str, attempts: int):
    _put_log('OTP_FAILURE', {'email': user_email, 'attempts': attempts})

def log_otp_max_attempts(user_email: str):
    _put_log('OTP_MAX_ATTEMPTS_EXCEEDED', {'email': user_email})

def log_note_created(user_id: str, note_id: str):
    _put_log('NOTE_CREATED', {'user_id': user_id, 'note_id': note_id})

def log_note_deleted(user_id: str, note_id: str):
    _put_log('NOTE_DELETED', {'user_id': user_id, 'note_id': note_id})

def log_note_accessed(user_id: str, note_id: str):
    _put_log('NOTE_ACCESSED', {'user_id': user_id, 'note_id': note_id})

def log_signup(user_email: str):
    _put_log('SIGNUP', {'email': user_email})

def log_error(error_msg: str, context: dict = None):
    _put_log('APP_ERROR', {'error': error_msg, 'context': context or {}})

def log_performance(endpoint: str, method: str, duration_ms: float):
    _put_log('PERFORMANCE_METRIC', {
        'endpoint': endpoint,
        'method': method,
        'duration_ms': round(duration_ms, 2)
    })
