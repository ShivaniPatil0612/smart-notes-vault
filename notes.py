"""
Smart Notes Vault - Notes Routes (CRUD)
/dashboard  /note/new  /note/<id>  /note/<id>/edit  /note/<id>/delete
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from datetime import datetime, timezone
from extensions import db
from models import NoteMetadata
from encryption import encrypt_note, decrypt_note
from s3_handler import upload_encrypted_note, download_encrypted_note, delete_encrypted_note
import cloudwatch_logger as cw
import logging
import uuid

notes_bp = Blueprint('notes', __name__)
logger   = logging.getLogger(__name__)


def make_s3_key(user_id: str, note_id: str) -> str:
    return f"notes/{user_id}/{note_id}.enc"


# ── Dashboard ─────────────────────────────────────────────────────────────────

@notes_bp.route('/dashboard')
@login_required
def dashboard():
    query = NoteMetadata.query.filter_by(user_id=current_user.id)

    search = request.args.get('q', '').strip()
    if search:
        query = query.filter(NoteMetadata.title.ilike(f'%{search}%'))

    tag_filter = request.args.get('tag', '').strip()
    if tag_filter:
        query = query.filter(NoteMetadata.tags.ilike(f'%{tag_filter}%'))

    pinned = query.filter_by(is_pinned=True).order_by(NoteMetadata.updated_at.desc()).all()
    others = query.filter_by(is_pinned=False).order_by(NoteMetadata.updated_at.desc()).all()
    notes  = pinned + others

    # Collect all unique tags across user's notes
    all_notes_for_tags = NoteMetadata.query.filter_by(user_id=current_user.id).all()
    all_tags = sorted(set(
        tag for note in all_notes_for_tags for tag in note.tags_list()
    ))

    return render_template('dashboard.html',
        notes=notes,
        search=search,
        tag_filter=tag_filter,
        all_tags=all_tags,
        note_count=NoteMetadata.query.filter_by(user_id=current_user.id).count()
    )


# ── Create Note ───────────────────────────────────────────────────────────────

@notes_bp.route('/note/new', methods=['GET', 'POST'])
@login_required
def new_note():
    if request.method == 'POST':
        title   = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        tags    = request.form.get('tags', '').strip()
        pinned  = request.form.get('is_pinned') == 'on'

        if not title:
            flash('Title is required.', 'error')
            return render_template('note_editor.html', mode='new',
                                   title=title, content=content, tags=tags)

        if not content:
            flash('Note content cannot be empty.', 'error')
            return render_template('note_editor.html', mode='new',
                                   title=title, content=content, tags=tags)

        note_id = str(uuid.uuid4())
        s3_key  = make_s3_key(current_user.id, note_id)

        try:
            ciphertext = encrypt_note(content)
        except Exception as e:
            flash('Encryption failed. Check server configuration.', 'error')
            logger.error(f"Encrypt error: {e}")
            return render_template('note_editor.html', mode='new',
                                   title=title, content=content, tags=tags)

        if not upload_encrypted_note(s3_key, ciphertext):
            flash('Failed to save note to cloud storage. Try again.', 'error')
            return render_template('note_editor.html', mode='new',
                                   title=title, content=content, tags=tags)

        word_count = len(content.split())
        note = NoteMetadata(
            id=note_id,
            user_id=current_user.id,
            title=title,
            s3_key=s3_key,
            tags=tags,
            is_pinned=pinned,
            word_count=word_count,
        )
        db.session.add(note)
        db.session.commit()

        cw.log_note_created(current_user.id, note_id)
        flash('Note saved securely.', 'success')
        return redirect(url_for('notes.view_note', note_id=note.id))

    return render_template('note_editor.html', mode='new',
                           title='', content='', tags='', is_pinned=False)


# ── View Note ─────────────────────────────────────────────────────────────────

@notes_bp.route('/note/<note_id>')
@login_required
def view_note(note_id):
    note = NoteMetadata.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()

    ciphertext = download_encrypted_note(note.s3_key)
    if ciphertext is None:
        flash('Could not retrieve note from cloud storage.', 'error')
        return redirect(url_for('notes.dashboard'))

    try:
        content = decrypt_note(ciphertext)
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('notes.dashboard'))

    cw.log_note_accessed(current_user.id, note_id)
    return render_template('view_note.html', note=note, content=content)


# ── Edit Note ─────────────────────────────────────────────────────────────────

@notes_bp.route('/note/<note_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_note(note_id):
    note = NoteMetadata.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        title   = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        tags    = request.form.get('tags', '').strip()
        pinned  = request.form.get('is_pinned') == 'on'

        if not title or not content:
            flash('Title and content are required.', 'error')
            return render_template('note_editor.html', mode='edit', note=note,
                                   title=title, content=content, tags=tags)

        try:
            ciphertext = encrypt_note(content)
        except Exception as e:
            flash('Encryption failed.', 'error')
            return render_template('note_editor.html', mode='edit', note=note,
                                   title=title, content=content, tags=tags)

        if not upload_encrypted_note(note.s3_key, ciphertext):
            flash('Failed to update note in cloud storage.', 'error')
            return render_template('note_editor.html', mode='edit', note=note,
                                   title=title, content=content, tags=tags)

        note.title      = title
        note.tags       = tags
        note.is_pinned  = pinned
        note.word_count = len(content.split())
        note.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        flash('Note updated.', 'success')
        return redirect(url_for('notes.view_note', note_id=note.id))

    # GET - load existing content
    ciphertext = download_encrypted_note(note.s3_key)
    content    = ''
    if ciphertext:
        try:
            content = decrypt_note(ciphertext)
        except ValueError:
            flash('Could not decrypt note for editing.', 'error')
            return redirect(url_for('notes.dashboard'))

    return render_template('note_editor.html', mode='edit', note=note,
                           title=note.title, content=content, tags=note.tags or '',
                           is_pinned=note.is_pinned)


# ── Delete Note ───────────────────────────────────────────────────────────────

@notes_bp.route('/note/<note_id>/delete', methods=['POST'])
@login_required
def delete_note(note_id):
    note = NoteMetadata.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()

    delete_encrypted_note(note.s3_key)
    db.session.delete(note)
    db.session.commit()

    cw.log_note_deleted(current_user.id, note_id)
    flash('Note deleted permanently.', 'info')
    return redirect(url_for('notes.dashboard'))


# ── Toggle Pin (AJAX) ─────────────────────────────────────────────────────────

@notes_bp.route('/note/<note_id>/pin', methods=['POST'])
@login_required
def toggle_pin(note_id):
    note = NoteMetadata.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()
    note.is_pinned = not note.is_pinned
    db.session.commit()
    return jsonify({'pinned': note.is_pinned})
