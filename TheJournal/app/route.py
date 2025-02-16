import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
from app import db, bcrypt
from app.models import User, JournalEntry, TimeCapsule
from config import Config

# Define blueprints for main and authentication routes
main_routes = Blueprint('main_routes', __name__)
auth_routes = Blueprint('auth_routes', __name__)

# Allowed file types
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'mp3', 'wav', 'ogg'}

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Serve uploaded files
@main_routes.route('/uploads/<path:filename>')
@login_required
def serve_media(filename):
    return send_from_directory(Config.UPLOAD_FOLDER, filename)

# Authentication Routes
@auth_routes.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("All fields are required!", "danger")
            return redirect(url_for('auth_routes.register'))

        if User.query.filter_by(username=username).first():
            flash("Username already exists!", "danger")
            return redirect(url_for('auth_routes.register'))

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth_routes.login'))

    return render_template('register.html')

@auth_routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main_routes.dashboard'))

        flash('Login failed. Check your username and password.', 'danger')

    return render_template('login.html')

@auth_routes.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main_routes.index'))

# Main Routes
@main_routes.route('/')
def index():
    return render_template('index.html')

@main_routes.route('/dashboard')
@login_required
def dashboard():
    journal_entries = JournalEntry.query.filter_by(user_id=current_user.id).all()
    time_capsules = TimeCapsule.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', journal_entries=journal_entries, time_capsules=time_capsules)

# Journal Entry Routes
@main_routes.route('/add_entry', methods=['GET', 'POST'])
@login_required
def add_entry():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        #get the mood 
        mood = request.form.get('mood', '').strip()

        if not title or not content:
            flash("Title and content are required!", "danger")
            return redirect(url_for('main_routes.add_entry'))

        video_path = save_uploaded_file('video')
      
        audio_path = save_uploaded_file('audio')

        entry = JournalEntry(
            title=title,
            content=content,
            mood=mood,
            video_path=video_path,
            audio_path=audio_path,
            user_id=current_user.id
        )

        db.session.add(entry)
        db.session.commit()

        flash('Journal entry added successfully!', 'success')
        return redirect(url_for('main_routes.dashboard'))

    return render_template('add_entry.html')

@main_routes.route('/add_time_capsule', methods=['GET', 'POST'])
@login_required
def add_time_capsule():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        mood = request.form.get('mood', '').strip()
        unlock_date_str = request.form.get('unlock_date', '')

        if not title or not content or not unlock_date_str:
            flash("All fields are required!", "danger")
            return redirect(url_for('main_routes.add_time_capsule'))

        try:
            unlock_date = datetime.strptime(unlock_date_str, '%Y-%m-%d')
        except ValueError:
            flash("Invalid date format!", "danger")
            return redirect(url_for('main_routes.add_time_capsule'))

        video_path = save_uploaded_file('video')
        audio_path = save_uploaded_file('audio')

        time_capsule = TimeCapsule(
            title=title,
            content=content,
            mood=mood,
            unlock_date=unlock_date,
            video_path=video_path,
            audio_path=audio_path,
            user_id=current_user.id
        )

        db.session.add(time_capsule)
        db.session.commit()

        flash('Time capsule added successfully!', 'success')
        return redirect(url_for('main_routes.dashboard'))

    return render_template('add_time_capsule.html')

@main_routes.route('/view_entry/<int:entry_id>')
@login_required
def view_entry(entry_id):
    entry = JournalEntry.query.get_or_404(entry_id)
    if entry.user_id != current_user.id:
        abort(403)

    return render_template('view_entry.html', entry=entry)

@main_routes.route('/view_time_capsule/<int:capsule_id>')
@login_required
def view_time_capsule(capsule_id):
    capsule = TimeCapsule.query.get_or_404(capsule_id)

    if capsule.user_id != current_user.id:
        abort(403)

    if datetime.utcnow() < capsule.unlock_date:
        flash('This time capsule is not yet unlocked.', 'warning')
        return redirect(url_for('main_routes.dashboard'))

    return render_template('view_time_capsule.html', capsule=capsule)

# Helper Function for File Uploads
def save_uploaded_file(field_name):
    """Saves uploaded video/audio files and returns a correctly formatted relative path."""
    file = request.files.get(field_name)
    if file and allowed_file(file.filename):
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)  # Ensure directory exists
        filename = secure_filename(f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}")
        
        # Use os.path.join but normalize it for URL paths
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(file_path)

        # Convert to a proper static URL path (force forward slashes)
        relative_path = f"uploads/{filename}"  

        return relative_path  # Store only the relative path in the database
    return None

    """Saves uploaded video/audio files and returns a correctly formatted relative path."""
    file = request.files.get(field_name)
    if file and allowed_file(file.filename):
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)  # Ensure directory exists
        filename = secure_filename(f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}")
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)

        # Fix Windows-style backslashes
        file_path = file_path.replace("\\", "/")  

        file.save(file_path)
        return f"uploads/{filename}"  # Store only the relative path
    return None
