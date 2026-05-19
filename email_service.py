"""
Smart Notes Vault - Email OTP Service
Uses SMTP (Brevo / AWS SES SMTP interface / any provider).
"""

import smtplib
import random
import string
import hashlib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import current_app

logger = logging.getLogger(__name__)


def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP."""
    return ''.join(random.choices(string.digits, k=length))


def hash_otp(otp: str) -> str:
    """Hash the OTP with SHA-256 before storing."""
    return hashlib.sha256(otp.encode()).hexdigest()


def verify_otp(plain_otp: str, stored_hash: str) -> bool:
    """Verify a plain OTP against its stored hash."""
    return hashlib.sha256(plain_otp.encode()).hexdigest() == stored_hash


def send_otp_email(recipient_email: str, otp: str, user_name: str) -> bool:
    """Send OTP email via SMTP."""
    cfg = current_app.config

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #0a0e1a; color: #e0e6f0; margin: 0; padding: 20px; }}
        .container {{ max-width: 500px; margin: auto; background: #111827; border-radius: 12px; padding: 40px; border: 1px solid #1e2d4a; }}
        .logo {{ font-size: 22px; font-weight: 700; color: #00d4aa; letter-spacing: 1px; margin-bottom: 24px; }}
        h2 {{ color: #e0e6f0; font-size: 20px; margin: 0 0 12px; }}
        .otp-box {{ background: #0a0e1a; border: 2px solid #00d4aa; border-radius: 10px;
                    text-align: center; padding: 24px; margin: 24px 0; }}
        .otp {{ font-size: 42px; font-weight: 800; letter-spacing: 10px; color: #00d4aa;
                font-family: 'Courier New', monospace; }}
        .note {{ font-size: 13px; color: #6b7a99; margin-top: 20px; }}
        .footer {{ font-size: 12px; color: #3d4f6b; margin-top: 30px; text-align: center; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="logo">🔐 Smart Notes Vault</div>
        <h2>Hello, {user_name}!</h2>
        <p>Use the One-Time Password below to verify your identity. It expires in <strong>10 minutes</strong>.</p>
        <div class="otp-box">
          <div class="otp">{otp}</div>
        </div>
        <p class="note">⚠️ Never share this code with anyone. Smart Notes Vault will never ask for it.</p>
        <div class="footer">This email was sent to {recipient_email}. If you didn't request this, ignore it.</div>
      </div>
    </body>
    </html>
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f'Your Smart Notes Vault OTP: {otp}'
    msg['From']    = cfg['MAIL_FROM']
    msg['To']      = recipient_email
    msg.attach(MIMEText(html_body, 'html'))

    # try:
    #     with smtplib.SMTP(cfg['MAIL_SERVER'], cfg['MAIL_PORT']) as server:
    #         server.ehlo()
    #         if cfg['MAIL_USE_TLS']:
    #             server.starttls()
    #             server.ehlo()
    #         if cfg['MAIL_USERNAME'] and cfg['MAIL_PASSWORD']:
    #             server.login(cfg['MAIL_USERNAME'], cfg['MAIL_PASSWORD'])
    #         server.sendmail(cfg['MAIL_FROM'], recipient_email, msg.as_string())
    #     logger.info(f"OTP email sent to {recipient_email}")
    #     return True
    # except smtplib.SMTPException as e:
    #     logger.error(f"Failed to send OTP email to {recipient_email}: {e}")
    #     return False

    try:
        # Print to terminal
        print(f"\n{'='*40}", flush=True)
        print(f"  DEV OTP for {recipient_email}: {otp}", flush=True)
        print(f"{'='*40}\n", flush=True)
        
        # Also write it to a file so it's never lost if the terminal clears!
        with open('latest_otp.txt', 'w', encoding='utf-8') as f:
            f.write(f"Your latest OTP for {recipient_email} is: {otp}\n")
            f.write("You can use this to log in!\n")
            
        return True
    except Exception as e:
        return False