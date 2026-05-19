from app import create_app
from extensions import db
from models import User

app = create_app()
app.app_context().push()

email = 'shivanikpatil126@gmail.com'
user = User.query.filter_by(email=email).first()

if not user:
    user = User(email=email, full_name='System Admin', role='admin', is_verified=True)
    db.session.add(user)

user.set_password('admin@123')
user.role = 'admin'
user.is_verified = True
db.session.commit()

print('Admin user configured successfully.')
