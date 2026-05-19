from app import create_app
from email_service import send_otp_email

app = create_app()
with app.app_context():
    print("Testing send_otp_email...")
    result = send_otp_email("test@example.com", "123456", "Test User")
    print(f"Result: {result}")
