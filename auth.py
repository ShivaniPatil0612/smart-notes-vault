"""
Smart Notes Vault - Authentication Routes
/signup  /login  /verify-otp  /logout
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timezone, timedelta
from extensions import db
from models import User, OTPRecord, NoteMetadata
from email_service import generate_otp, hash_otp, verify_otp as check_otp, send_otp_email
import cloudwatch_logger as cw
import logging

auth_bp = Blueprint('auth', __name__)
logger  = logging.getLogger(__name__)

OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS   = 5


# ── Signup ────────────────────────────────────────────────────────────────────

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('notes.dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email     = request.form.get('email', '').strip().lower()
        password  = request.form.get('password', '')
        confirm   = request.form.get('confirm_password', '')

        # Validation
        if not all([full_name, email, password, confirm]):
            flash('All fields are required.', 'error')
            return render_template('signup.html')

        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('signup.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return render_template('signup.html')

        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'error')
            return render_template('signup.html')

        # Create user
        user = User(email=email, full_name=full_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        cw.log_signup(email)

        # Send OTP for email verification
        otp      = generate_otp()
        otp_hash = hash_otp(otp)
        expires  = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

        otp_record = OTPRecord(user_id=user.id, otp_hash=otp_hash, expires_at=expires)
        db.session.add(otp_record)
        db.session.commit()

        if send_otp_email(email, otp, full_name):
            session['otp_user_id'] = user.id
            flash(f'Account created! (DEV MODE OTP: {otp}) Check your email for the OTP to verify.', 'success')
            return redirect(url_for('auth.verify_otp'))
        else:
            flash(f'Account created but OTP email failed. (DEV MODE OTP: {otp}) Contact support.', 'warning')
            return redirect(url_for('auth.login'))

    return render_template('signup.html')


# ── Login ─────────────────────────────────────────────────────────────────────

@auth_bp.route('/', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('notes.dashboard'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            cw.log_login_failure(email, 'invalid credentials')
            flash('Invalid email or password.', 'error')
            return render_template('login.html')

        if not user.is_active:
            flash('Your account has been disabled. Contact support.', 'error')
            return render_template('login.html')

        # Admin Bypass OTP
        if user.role == 'admin':
            login_user(user, remember=False)
            cw.log_login_success(user.email)
            flash('Welcome, Administrator!', 'success')
            return redirect(url_for('auth.admin_dashboard'))

        # Generate & send OTP
        otp      = generate_otp()
        otp_hash = hash_otp(otp)
        expires  = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

        otp_record = OTPRecord.query.filter_by(user_id=user.id).first()
        if otp_record:
            otp_record.otp_hash   = otp_hash
            otp_record.expires_at = expires
            otp_record.attempts   = 0
        else:
            otp_record = OTPRecord(user_id=user.id, otp_hash=otp_hash, expires_at=expires)
            db.session.add(otp_record)
        db.session.commit()

        if send_otp_email(email, otp, user.full_name):
            session['otp_user_id'] = user.id
            flash(f'OTP sent to {email}. Valid for {OTP_EXPIRY_MINUTES} minutes. (DEV MODE OTP: {otp})', 'info')
            return redirect(url_for('auth.verify_otp'))
        else:
            flash(f'Failed to send OTP. (DEV MODE OTP: {otp}) Please try again.', 'error')
            return render_template('login.html')

    return render_template('login.html')


# ── OTP Verification ──────────────────────────────────────────────────────────

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    user_id = session.get('otp_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user:
        session.pop('otp_user_id', None)
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        otp_input  = request.form.get('otp', '').strip()
        otp_record = OTPRecord.query.filter_by(user_id=user_id).first()

        if not otp_record:
            flash('OTP not found. Please log in again.', 'error')
            return redirect(url_for('auth.login'))

        if otp_record.is_expired():
            flash('OTP has expired. Please log in again.', 'error')
            return redirect(url_for('auth.login'))

        if otp_record.attempts >= OTP_MAX_ATTEMPTS:
            cw.log_otp_max_attempts(user.email)
            flash('Too many failed attempts. Please log in again.', 'error')
            return redirect(url_for('auth.login'))

        if check_otp(otp_input, otp_record.otp_hash):
            # Success
            otp_record.attempts = 0
            user.is_verified    = True
            user.last_login     = datetime.now(timezone.utc)
            db.session.delete(otp_record)
            db.session.commit()

            session.pop('otp_user_id', None)
            login_user(user, remember=False)
            cw.log_login_success(user.email)
            flash('Welcome to your vault!', 'success')
            return redirect(url_for('notes.dashboard'))
        else:
            otp_record.attempts += 1
            db.session.commit()
            remaining = OTP_MAX_ATTEMPTS - otp_record.attempts
            cw.log_otp_failure(user.email, otp_record.attempts)
            flash(f'Invalid OTP. {remaining} attempt(s) remaining.', 'error')

    return render_template('otp.html', email=user.email)


# ── Resend OTP ────────────────────────────────────────────────────────────────

@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    user_id = session.get('otp_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('auth.login'))

    otp      = generate_otp()
    otp_hash = hash_otp(otp)
    expires  = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    otp_record = OTPRecord.query.filter_by(user_id=user_id).first()
    if otp_record:
        otp_record.otp_hash   = otp_hash
        otp_record.expires_at = expires
        otp_record.attempts   = 0
    else:
        otp_record = OTPRecord(user_id=user.id, otp_hash=otp_hash, expires_at=expires)
        db.session.add(otp_record)
    db.session.commit()

    if send_otp_email(user.email, otp, user.full_name):
        flash(f'A new OTP has been sent. (DEV MODE OTP: {otp})', 'success')
    else:
        flash(f'Failed to resend OTP. (DEV MODE OTP: {otp})', 'error')

    return redirect(url_for('auth.verify_otp'))


# ── Logout ────────────────────────────────────────────────────────────────────

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('auth.login'))

# ── Admin Dashboard ───────────────────────────────────────────────────────────

@auth_bp.route('/admin')
@login_required
def admin_dashboard():
    # Restrict to admin role
    if current_user.role != 'admin':
        flash('Access denied. Admin only.', 'error')
        return redirect(url_for('notes.dashboard'))

    users = User.query.order_by(User.created_at.desc()).all()
    user_data = []
    for u in users:
        note_count = NoteMetadata.query.filter_by(user_id=u.id).count()
        user_data.append({
            'name': u.full_name,
            'email': u.email,
            'registered_at': u.created_at,
            'note_count': note_count
        })
    
    return render_template('admin.html', total_users=len(users), user_data=user_data)
