# app.py
# Main Flask Application for MindEase
# Uses Flask 3.0.0, Flask-SQLAlchemy 3.1.1, Flask-Login 0.6.3

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import random

# Load environment variables
load_dotenv()

# Import database models
from models import db, User, Profile, ChatSession, ChatMessage, PreSurvey, PostSurvey, JournalEntry, BreathingSession, DailyMotivation, Admin, calculate_effectiveness, get_quote_for_emotion, QUOTE_EMOTIONS
from functools import wraps
from sqlalchemy import inspect as sa_inspect, text as sa_text

# Import Gemini chatbot
from gemini_api import create_chatbot

# Import configuration
from config import Config

# ============================================================================
# FLASK APPLICATION INITIALIZATION
# ============================================================================

app = Flask(__name__)
app.config.from_object(Config)

# Force a clean absolute path directory to resolve Windows environment bugs
_BASE_DIR = os.path.abspath(os.path.dirname(__file__))
_INSTANCE_DIR = os.path.join(_BASE_DIR, "instance")

# Ensure the instance directory physically exists on disk
if not os.path.exists(_INSTANCE_DIR):
    os.makedirs(_INSTANCE_DIR)

# Force overwrite the connection string with the exact absolute path mapping
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(_INSTANCE_DIR, 'mindease.db')}"

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Create database tables
with app.app_context():
    db.create_all()

    # Lightweight migration: add the 'emotion' column to existing databases
    # (db.create_all does not alter tables that already exist).
    _cols = [c['name'] for c in sa_inspect(db.engine).get_columns('daily_motivation')]
    if 'emotion' not in _cols:
        db.session.execute(sa_text(
            "ALTER TABLE daily_motivation ADD COLUMN emotion "
            "VARCHAR(20) NOT NULL DEFAULT 'general'"
        ))
        db.session.commit()
        print("Migrated: added 'emotion' column to daily_motivation")

    # Seed a few emotion-specific quotes if a category has none yet, so the
    # mood-adaptive feature has content out of the box.
    _emotion_seed = {
        'Happy': [
            ('Happiness is not something ready made. It comes from your own actions.', 'Dalai Lama'),
            ('Celebrate the small wins; they add up to big victories.', 'Anonymous'),
        ],
        'Calm': [
            ('Within you there is a stillness and a sanctuary to which you can retreat at any time.', 'Hermann Hesse'),
            ('Calm mind brings inner strength and self-confidence.', 'Dalai Lama'),
        ],
        'Stressed': [
            ('You don\'t have to control your thoughts. You just have to stop letting them control you.', 'Dan Millman'),
            ('Almost everything will work again if you unplug it for a few minutes, including you.', 'Anne Lamott'),
        ],
        'Sad': [
            ('Even the darkest night will end and the sun will rise.', 'Victor Hugo'),
            ('Your present circumstances don\'t determine where you can go; they merely determine where you start.', 'Nido Qubein'),
        ],
        'Anxious': [
            ('You don\'t have to see the whole staircase, just take the first step.', 'Martin Luther King Jr.'),
            ('Nothing diminishes anxiety faster than action.', 'Walter Anderson'),
        ],
    }
    for _emotion, _pairs in _emotion_seed.items():
        if DailyMotivation.query.filter_by(emotion=_emotion).count() == 0:
            for _text, _author in _pairs:
                db.session.add(DailyMotivation(
                    quote_text=_text, author=_author, is_active=True, emotion=_emotion
                ))
    db.session.commit()

    # Seed default admin account if none exists (Use Case 11 from FYP1)
    # Credentials configurable via .env: ADMIN_USERNAME / ADMIN_PASSWORD
    if Admin.query.count() == 0:
        default_admin = Admin(username=os.getenv('ADMIN_USERNAME', 'admin'))
        default_admin.set_password(os.getenv('ADMIN_PASSWORD', 'AdminPass456'))
        db.session.add(default_admin)
        db.session.commit()
        print("Default admin account created (username: "
              f"{default_admin.username})")

# Initialize Gemini chatbot
try:
    chatbot = create_chatbot()
except Exception as e:
    print(f"Warning: Could not initialize Gemini chatbot: {e}")
    chatbot = None

# ============================================================================
# FLASK-LOGIN USER LOADER
# ============================================================================

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))

# ============================================================================
# TEMPLATE FILTERS (for Jinja2 templates)
# ============================================================================

@app.template_filter('datetime_format')
def datetime_format(value, format='%b %d, %Y - %I:%M%p'):
    """Format datetime for display"""
    if value is None:
        return ""
    return value.strftime(format)

#Login Page 

@app.route('/')
def index():
    """
    Home page - redirects to dashboard if logged in, otherwise shows login
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login route - handles user authentication
    Implements Werkzeug password verification as per FYP report
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validate input
        if not email or not password:
            flash('Please provide both email and password.', 'error')
            return render_template('index.html')
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        # Verify credentials
        if user and user.check_password(password):
            # Login successful
            login_user(user, remember=True)
            flash(f'Welcome back, {user.email}!', 'success')
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            # Login failed
            flash('Invalid email or password. Please try again.', 'error')
            return render_template('index.html')
    
    return render_template('index.html')

# Registration

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Registration route - creates new user account
    Implements password hashing with Werkzeug as per FYP report
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirmPassword')
        fullname = request.form.get('fullname', '').strip()
        age_group = request.form.get('ageGroup', '').strip()
        
        # Validate input
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('register.html')
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email already exists.', 'error')
            return render_template('register.html')
        
        # Create new user
        new_user = User(email=email)
        new_user.set_password(password)  # Hash password with Werkzeug
        
        try:
            db.session.add(new_user)
            db.session.commit()
            
            # Create profile if name or age group provided
            if fullname or age_group:
                profile = Profile(
                    user_id=new_user.id,
                    name=fullname if fullname else None,
                    age_group=age_group if age_group else None
                )
                db.session.add(profile)
                db.session.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
            print(f"Registration error: {e}")
            return render_template('register.html')
    
    return render_template('register.html')

# Dashboard

@app.route('/dashboard')
@login_required
def dashboard():
    """
    Dashboard - main hub showing statistics and quick actions
    Implements dashboard features from FYP report
    """
    # Get user statistics
    total_sessions = ChatSession.query.filter_by(user_id=current_user.id).count()
    
    # Calculate average stress reduction and build trend data over time
    # (stress trends dashboard: 80% of FYP1 survey respondents wanted this)
    completed_sessions = ChatSession.query.filter_by(user_id=current_user.id).filter(
        ChatSession.end_time.isnot(None)
    ).order_by(ChatSession.start_time).all()

    stress_reductions = []
    trend_data = []
    for cs in completed_sessions:
        effectiveness = calculate_effectiveness(cs.id)
        if effectiveness:
            trend_data.append({
                'date': cs.start_time.strftime('%d %b'),
                'improvement': effectiveness['overall_improvement'],
                'pre': effectiveness['pre_total'],
                'post': effectiveness['post_total']
            })
            if effectiveness['overall_improvement'] > 0:
                stress_reductions.append(effectiveness['overall_improvement'])

    avg_stress_reduction = round(sum(stress_reductions) / len(stress_reductions)) if stress_reductions else 0
    
    # Get total journal entries
    total_journals = JournalEntry.query.filter_by(user_id=current_user.id).count()
    
    # Get a motivational quote adapted to the user's current mood
    # (mood is chosen via the dashboard picker and remembered in the session)
    current_mood = session.get('current_mood', 'Neutral')
    daily_quote = get_quote_for_emotion(current_mood)

    # Get user name for welcome message
    user_name = current_user.email.split('@')[0]  # Default to email prefix
    if current_user.profile and current_user.profile.name:
        user_name = current_user.profile.name

    return render_template('dashboard.html',
                         user_name=user_name,
                         total_sessions=total_sessions,
                         avg_stress_reduction=avg_stress_reduction,
                         total_journals=total_journals,
                         daily_quote=daily_quote,
                         current_mood=current_mood,
                         mood_options=QUOTE_EMOTIONS,
                         trend_data=trend_data)

# Pre-session assesment
@app.route('/pre-assessment', methods=['GET', 'POST'])
@login_required
def pre_assessment():
    """
    Pre-session assessment - 5-question stress assessment before chat
    Implements PreSurvey from FYP report
    """
    if request.method == 'POST':
        # Get form data
        stress = request.form.get('stress', type=int)
        mood = request.form.get('mood', type=int)
        sleep = request.form.get('sleep', type=int)
        energy = request.form.get('energy', type=int)
        anxiety = request.form.get('anxiety', type=int)
        
        # Validate all fields provided
        if not all([stress, mood, sleep, energy, anxiety]):
            flash('Please answer all questions.', 'error')
            return render_template('pre-assessment.html')
        
        # Validate range (1-5)
        if not all(1 <= x <= 5 for x in [stress, mood, sleep, energy, anxiety]):
            flash('Invalid assessment values.', 'error')
            return render_template('pre-assessment.html')
        
        try:
            # Create new chat session
            new_session = ChatSession(
                user_id=current_user.id,
                initial_stress_level=stress
            )
            db.session.add(new_session)
            db.session.flush()  # Get session ID without committing
            
            # Create pre-survey record
            pre_survey = PreSurvey(
                session_id=new_session.id,
                stress_level=stress,
                mood=mood,
                sleep_quality=sleep,
                energy_level=energy,
                anxiety_level=anxiety
            )
            db.session.add(pre_survey)
            db.session.commit()
            
            # Store session ID in Flask session for chat page
            session['current_session_id'] = new_session.id
            
            flash('Assessment completed. Starting your session...', 'success')
            return redirect(url_for('chat'))
        
        except Exception as e:
            db.session.rollback()
            flash('Error starting session. Please try again.', 'error')
            print(f"Pre-assessment error: {e}")
            return render_template('pre-assessment.html')
    
    return render_template('pre-assessment.html')

# ============================================================================
# ROUTE 5: CHAT INTERFACE
# ============================================================================

@app.route('/chat')
@login_required
def chat():
    """
    Chat interface - main conversation page
    Displays ongoing chat session
    """
    # Get current session ID from Flask session
    session_id = session.get('current_session_id')
    
    if not session_id:
        flash('No active session. Please start a new session.', 'warning')
        return redirect(url_for('pre_assessment'))
    
    # Get chat session from database
    chat_session = ChatSession.query.get(session_id)
    
    if not chat_session or chat_session.user_id != current_user.id:
        flash('Invalid session. Please start a new session.', 'error')
        return redirect(url_for('pre_assessment'))
    
    # Check if session already ended
    if chat_session.end_time:
        flash('This session has ended. Please start a new session.', 'info')
        return redirect(url_for('pre_assessment'))
    
    # Get all messages for this session
    messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.timestamp).all()
    
    # Get stress level from pre-assessment
    stress_level = chat_session.initial_stress_level or 3
    
    # Generate initial bot message if no messages yet
    if len(messages) == 0 and chatbot:
        try:
            initial_message = chatbot.get_conversation_starter(stress_level)
            
            # Save bot's initial message
            bot_message = ChatMessage(
                session_id=session_id,
                sender='bot',
                message_text=initial_message
            )
            db.session.add(bot_message)
            db.session.commit()
            
            # Reload messages
            messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.timestamp).all()
        except Exception as e:
            print(f"Error generating initial message: {e}")
    
    return render_template('chat.html',
                         session_id=session_id,
                         stress_level=stress_level,
                         messages=messages)

# ============================================================================
# ROUTE 6: SEND MESSAGE (AJAX API)
# ============================================================================

@app.route('/api/send-message', methods=['POST'])
@login_required
def send_message():
    """
    API endpoint for sending chat messages
    Handles Gemini API integration for bot responses
    """
    try:
        data = request.get_json()
        message_text = data.get('message', '').strip()
        session_id = data.get('session_id')
        
        if not message_text or not session_id:
            return jsonify({'error': 'Invalid request'}), 400
        
        # Verify session belongs to current user
        chat_session = ChatSession.query.get(session_id)
        if not chat_session or chat_session.user_id != current_user.id:
            return jsonify({'error': 'Invalid session'}), 403
        
        # Check session not ended
        if chat_session.end_time:
            return jsonify({'error': 'Session has ended'}), 400
        
        # Save user message
        user_message = ChatMessage(
            session_id=session_id,
            sender='user',
            message_text=message_text
        )
        db.session.add(user_message)
        db.session.commit()
        
        # Generate bot response using Gemini API
        if chatbot:
            # Get conversation history for context
            previous_messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.timestamp).all()
            conversation_history = [
                {'sender': msg.sender, 'message': msg.message_text}
                for msg in previous_messages[-10:]  # Last 5 exchanges
            ]
            
            # Get stress level
            stress_level = chat_session.initial_stress_level or 3
            
            # Generate response
            try:
                bot_response_text = chatbot.generate_response(
                    message_text,
                    stress_level,
                    conversation_history
                )
            except Exception as e:
                print(f"Gemini API error: {e}")
                bot_response_text = "I'm experiencing a small technical issue, but I'm still here to listen. What would you like to talk about?"
        else:
            bot_response_text = "I'm here to support you. Could you tell me more about what's on your mind?"
        
        # Save bot response
        bot_message = ChatMessage(
            session_id=session_id,
            sender='bot',
            message_text=bot_response_text
        )
        db.session.add(bot_message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'bot_message': bot_response_text,
            'timestamp': bot_message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    except Exception as e:
        print(f"Send message error: {e}")
        return jsonify({'error': 'Server error'}), 500

# To end session

@app.route('/end-session/<int:session_id>', methods=['POST'])
@login_required
def end_session(session_id):
    """
    End the current chat session
    Sets end_time and redirects to post-assessment
    """
    chat_session = ChatSession.query.get(session_id)
    
    if not chat_session or chat_session.user_id != current_user.id:
        flash('Invalid session.', 'error')
        return redirect(url_for('dashboard'))
    
    # Set end time
    chat_session.end_time = datetime.utcnow()
    db.session.commit()
    
    # Store session ID for post-assessment
    session['current_session_id'] = session_id
    
    return redirect(url_for('post_assessment'))

# Post-Session Assessemnt

@app.route('/post-assessment', methods=['GET', 'POST'])
@login_required
def post_assessment():
    """
    Post-session assessment - same 5 questions after chat
    Implements PostSurvey from FYP report
    """
    session_id = session.get('current_session_id')
    
    if not session_id:
        flash('No session to assess. Please start a new session.', 'warning')
        return redirect(url_for('pre_assessment'))
    
    chat_session = ChatSession.query.get(session_id)
    
    if not chat_session or chat_session.user_id != current_user.id:
        flash('Invalid session.', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if post-survey already exists
    if chat_session.post_survey:
        flash('You have already completed this assessment.', 'info')
        return redirect(url_for('comparison', session_id=session_id))
    
    if request.method == 'POST':
        # Get form data
        stress = request.form.get('stress', type=int)
        mood = request.form.get('mood', type=int)
        sleep = request.form.get('sleep', type=int)
        energy = request.form.get('energy', type=int)
        anxiety = request.form.get('anxiety', type=int)
        
        # Validate
        if not all([stress, mood, sleep, energy, anxiety]):
            flash('Please answer all questions.', 'error')
            return render_template('post-assessment.html')
        
        if not all(1 <= x <= 5 for x in [stress, mood, sleep, energy, anxiety]):
            flash('Invalid assessment values.', 'error')
            return render_template('post-assessment.html')
        
        try:
            # Create post-survey record
            post_survey = PostSurvey(
                session_id=session_id,
                stress_level=stress,
                mood=mood,
                sleep_quality=sleep,
                energy_level=energy,
                anxiety_level=anxiety
            )
            db.session.add(post_survey)
            db.session.commit()
            
            flash('Assessment completed!', 'success')
            return redirect(url_for('comparison', session_id=session_id))
        
        except Exception as e:
            db.session.rollback()
            flash('Error saving assessment. Please try again.', 'error')
            print(f"Post-assessment error: {e}")
            return render_template('post-assessment.html')
    
    return render_template('post-assessment.html')

# Comparison/Results

@app.route('/comparison/<int:session_id>')
@login_required
def comparison(session_id):
    """
    Comparison page - shows before/after results
    Implements effectiveness calculation from FYP report
    """
    chat_session = ChatSession.query.get(session_id)
    
    if not chat_session or chat_session.user_id != current_user.id:
        flash('Invalid session.', 'error')
        return redirect(url_for('dashboard'))
    
    
    effectiveness = calculate_effectiveness(session_id)

    if not effectiveness:
        flash('Cannot calculate effectiveness. Assessment data missing.', 'error')
        return redirect(url_for('dashboard'))

    # Full conversation transcript (IT-03: session details show transcript)
    messages = ChatMessage.query.filter_by(session_id=session_id).order_by(
        ChatMessage.timestamp
    ).all()

    return render_template('comparison.html',
                         session=chat_session,
                         effectiveness=effectiveness,
                         messages=messages)

# Session History

@app.route('/history')
@login_required
def history():
    """
    Session history - displays all past sessions with effectiveness
    Implements history tracking from FYP report
    """
    # Get all completed sessions (with end_time)
    sessions = ChatSession.query.filter_by(user_id=current_user.id).filter(
        ChatSession.end_time.isnot(None)
    ).order_by(ChatSession.start_time.desc()).all()
    
    # Calculate effectiveness for each session
    sessions_with_effectiveness = []
    for session in sessions:
        effectiveness = calculate_effectiveness(session.id)
        sessions_with_effectiveness.append({
            'session': session,
            'effectiveness': effectiveness,
            'duration_minutes': session.get_duration_minutes(),
            'message_count': session.get_message_count()
        })
    
    return render_template('history.html', sessions=sessions_with_effectiveness)

# Breathing Exercises

@app.route('/breathing')
@login_required
def breathing():
    """
    Breathing exercises page - displays 3 techniques
    Implements wellness tools from FYP report
    """
    return render_template('breathing.html')

@app.route('/api/complete-breathing', methods=['POST'])
@login_required
def complete_breathing():
    """
    API endpoint to track breathing exercise completion
    """
    try:
        data = request.get_json()
        technique = data.get('technique')
        
        if not technique:
            return jsonify({'error': 'Invalid request'}), 400
        
        # Create breathing session record
        breathing_session = BreathingSession(
            user_id=current_user.id,
            technique=technique
        )
        db.session.add(breathing_session)
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        print(f"Complete breathing error: {e}")
        return jsonify({'error': 'Server error'}), 500

# Journaling Feature

@app.route('/journal', methods=['GET', 'POST'])
@login_required
def journal():
    """
    Journal entry page - create new journal entries
    Implements journaling from FYP report
    """
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        mood = request.form.get('mood', '').strip()
        
        if not title or not content:
            flash('Title and content are required.', 'error')
            return render_template('journal.html')
        
        try:
            # Create journal entry
            entry = JournalEntry(
                user_id=current_user.id,
                title=title,
                content=content,
                mood=mood if mood else None
            )
            db.session.add(entry)
            db.session.commit()
            
            flash('Journal entry saved successfully!', 'success')
            return redirect(url_for('journal_entries'))
        
        except Exception as e:
            db.session.rollback()
            flash('Error saving journal entry.', 'error')
            print(f"Journal error: {e}")
            return render_template('journal.html')
    
    return render_template('journal.html')

@app.route('/api/random-quote')
@login_required
def random_quote():
    """
    Return a motivational quote as JSON, adapted to the requested emotion,
    so the dashboard can refresh without reloading. When an 'emotion' query
    param is given it is remembered in the session as the user's current mood.
    """
    emotion = request.args.get('emotion')
    if emotion is not None:
        session['current_mood'] = emotion          # remember the selection
    else:
        emotion = session.get('current_mood', 'Neutral')

    quote = get_quote_for_emotion(emotion)
    if not quote:
        return jsonify({'success': False}), 404
    return jsonify({
        'success': True,
        'quote_text': quote.quote_text,
        'author': quote.author or 'Unknown',
        'emotion': emotion or 'Neutral'
    })

@app.route('/journal/entries')
@login_required
def journal_entries():
    """
    List all of the current user's journal entries, newest first
    """
    entries = JournalEntry.query.filter_by(user_id=current_user.id).order_by(
        JournalEntry.created_at.desc()
    ).all()
    return render_template('journal-entries.html', entries=entries)

@app.route('/journal/edit/<int:entry_id>', methods=['GET', 'POST'])
@login_required
def journal_edit(entry_id):
    """
    Edit an existing journal entry (owner only)
    """
    entry = JournalEntry.query.get(entry_id)

    if not entry or entry.user_id != current_user.id:
        flash('Journal entry not found.', 'error')
        return redirect(url_for('journal_entries'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        mood = request.form.get('mood', '').strip()

        if not title or not content:
            flash('Title and content are required.', 'error')
            return render_template('journal.html', entry=entry)

        try:
            entry.title = title
            entry.content = content
            entry.mood = mood if mood else None
            db.session.commit()

            flash('Journal entry updated!', 'success')
            return redirect(url_for('journal_entries'))

        except Exception as e:
            db.session.rollback()
            flash('Error updating journal entry.', 'error')
            print(f"Journal edit error: {e}")

    return render_template('journal.html', entry=entry)

@app.route('/journal/delete/<int:entry_id>', methods=['POST'])
@login_required
def journal_delete(entry_id):
    """
    Delete a journal entry (owner only)
    """
    entry = JournalEntry.query.get(entry_id)

    if not entry or entry.user_id != current_user.id:
        flash('Journal entry not found.', 'error')
        return redirect(url_for('journal_entries'))

    try:
        db.session.delete(entry)
        db.session.commit()
        flash('Journal entry deleted.', 'info')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting journal entry.', 'error')
        print(f"Journal delete error: {e}")

    return redirect(url_for('journal_entries'))

# ============================================================================
# ROUTE 13: LOGOUT
# ============================================================================

@app.route('/logout')
@login_required
def logout():
    """
    Logout route - ends user session
    """
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# ============================================================================
# ADMIN MODULE (Use Cases 11-12 from FYP1: Admin Login, Quote Management)
# Admin auth is separate from user auth (Flask session flag, not Flask-Login)
# Privacy by design: admin sees aggregate statistics only - never user
# conversations, journals or individual assessment answers.
# ============================================================================

def admin_required(f):
    """Guard admin routes - redirects to admin login if not authenticated"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('admin_id'):
            flash('Please log in as administrator.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrapper

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """
    Admin login - independent from user authentication (UT-05)
    """
    if session.get('admin_id'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        admin = Admin.query.filter_by(username=username).first()

        if admin and admin.check_password(password):
            session['admin_id'] = admin.id
            flash('Welcome, administrator!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials.', 'error')

    return render_template('admin-login.html')

@app.route('/admin/logout')
def admin_logout():
    """End the admin session"""
    session.pop('admin_id', None)
    flash('Admin logged out.', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    """
    Admin dashboard - aggregate, anonymous usage statistics only
    """
    total_users = User.query.count()
    total_sessions = ChatSession.query.count()
    completed_sessions = ChatSession.query.filter(
        ChatSession.end_time.isnot(None)
    ).count()
    total_messages = ChatMessage.query.count()
    total_journals = JournalEntry.query.count()
    total_breathing = BreathingSession.query.count()
    active_quotes = DailyMotivation.query.filter_by(is_active=True).count()

    # Average improvement across all completed sessions (anonymous aggregate)
    improvements = []
    for s in ChatSession.query.filter(ChatSession.end_time.isnot(None)).all():
        eff = calculate_effectiveness(s.id)
        if eff:
            improvements.append(eff['overall_improvement'])
    avg_improvement = round(sum(improvements) / len(improvements), 1) if improvements else 0

    return render_template('admin-dashboard.html',
                           total_users=total_users,
                           total_sessions=total_sessions,
                           completed_sessions=completed_sessions,
                           total_messages=total_messages,
                           total_journals=total_journals,
                           total_breathing=total_breathing,
                           active_quotes=active_quotes,
                           avg_improvement=avg_improvement)

@app.route('/admin/quotes', methods=['GET', 'POST'])
@admin_required
def admin_quotes():
    """
    Quote management - add new motivational quotes (IT-04)
    """
    if request.method == 'POST':
        quote_text = request.form.get('quote_text', '').strip()
        author = request.form.get('author', '').strip()
        emotion = request.form.get('emotion', 'general').strip() or 'general'

        if not quote_text:
            flash('Quote text is required.', 'error')
        else:
            try:
                quote = DailyMotivation(
                    quote_text=quote_text,
                    author=author if author else None,
                    is_active=True,
                    emotion=emotion
                )
                db.session.add(quote)
                db.session.commit()
                flash('Quote added successfully!', 'success')
                return redirect(url_for('admin_quotes'))
            except Exception as e:
                db.session.rollback()
                flash('Error adding quote.', 'error')
                print(f"Add quote error: {e}")

    quotes = DailyMotivation.query.order_by(DailyMotivation.created_at.desc()).all()
    # Emotion options for the dropdown: specific moods + General
    emotion_options = ['general'] + [e for e in QUOTE_EMOTIONS if e != 'Neutral']
    return render_template('admin-quotes.html', quotes=quotes, emotion_options=emotion_options)

@app.route('/admin/quotes/toggle/<int:quote_id>', methods=['POST'])
@admin_required
def admin_quote_toggle(quote_id):
    """Activate/deactivate a quote (uses the is_active flag from the ERD)"""
    quote = DailyMotivation.query.get(quote_id)
    if quote:
        quote.is_active = not quote.is_active
        db.session.commit()
        state = 'activated' if quote.is_active else 'deactivated'
        flash(f'Quote {state}.', 'info')
    return redirect(url_for('admin_quotes'))

@app.route('/admin/quotes/delete/<int:quote_id>', methods=['POST'])
@admin_required
def admin_quote_delete(quote_id):
    """Permanently remove a quote"""
    quote = DailyMotivation.query.get(quote_id)
    if quote:
        db.session.delete(quote)
        db.session.commit()
        flash('Quote deleted.', 'info')
    return redirect(url_for('admin_quotes'))

# ---------------------------------------------------------------------------
# Admin: User Management (account administration)
# Admin can list/add/remove accounts and see per-user ACTIVITY COUNTS only.
# Conversation text and journal content are never exposed - privacy by design.
# ---------------------------------------------------------------------------

@app.route('/admin/users')
@admin_required
def admin_users():
    """List all user accounts with aggregate activity counts (no content)."""
    users = User.query.order_by(User.created_at.desc()).all()
    user_rows = []
    for u in users:
        session_count = ChatSession.query.filter_by(user_id=u.id).count()
        journal_count = JournalEntry.query.filter_by(user_id=u.id).count()
        user_rows.append({
            'id': u.id,
            'email': u.email,
            'name': u.profile.name if u.profile and u.profile.name else '-',
            'age_group': u.profile.age_group if u.profile and u.profile.age_group else '-',
            'created_at': u.created_at,
            'sessions': session_count,
            'journals': journal_count
        })
    return render_template('admin-users.html', users=user_rows)

@app.route('/admin/users/add', methods=['POST'])
@admin_required
def admin_user_add():
    """Create a new user account from the admin panel."""
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    name = request.form.get('name', '').strip()

    if not email or not password:
        flash('Email and password are required.', 'error')
        return redirect(url_for('admin_users'))

    if len(password) < 8:
        flash('Password must be at least 8 characters.', 'error')
        return redirect(url_for('admin_users'))

    if User.query.filter_by(email=email).first():
        flash('An account with this email already exists.', 'error')
        return redirect(url_for('admin_users'))

    try:
        new_user = User(email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush()
        if name:
            db.session.add(Profile(user_id=new_user.id, name=name))
        db.session.commit()
        flash(f'User {email} created.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error creating user.', 'error')
        print(f"Admin add user error: {e}")

    return redirect(url_for('admin_users'))

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_user_delete(user_id):
    """Delete a user account and all their data (cascade)."""
    user = User.query.get(user_id)
    if user:
        try:
            email = user.email
            db.session.delete(user)  # cascades to sessions, journals, etc.
            db.session.commit()
            flash(f'User {email} and all their data deleted.', 'info')
        except Exception as e:
            db.session.rollback()
            flash('Error deleting user.', 'error')
            print(f"Admin delete user error: {e}")
    else:
        flash('User not found.', 'error')
    return redirect(url_for('admin_users'))

# ---------------------------------------------------------------------------
# Admin: Analytics (aggregate, anonymous data visualisations)
# ---------------------------------------------------------------------------

@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    """Aggregate visualisations of system-wide, anonymous data."""
    from collections import defaultdict

    # 1. User registrations per day (cumulative growth)
    reg_by_day = defaultdict(int)
    for u in User.query.all():
        reg_by_day[u.created_at.strftime('%d %b')] += 1
    # Preserve chronological order
    reg_sorted = sorted(User.query.all(), key=lambda u: u.created_at)
    reg_labels, reg_counts, running = [], [], 0
    seen = set()
    for u in reg_sorted:
        day = u.created_at.strftime('%d %b')
        running += 1
        if day in seen:
            reg_counts[-1] = running
        else:
            seen.add(day)
            reg_labels.append(day)
            reg_counts.append(running)

    # 2. Sessions per day
    sess_by_day = defaultdict(int)
    for s in ChatSession.query.all():
        sess_by_day[s.start_time.strftime('%d %b')] += 1
    sess_labels = sorted(sess_by_day.keys(),
                         key=lambda d: datetime.strptime(d, '%d %b'))
    sess_counts = [sess_by_day[d] for d in sess_labels]

    # 3. Journal mood distribution (anonymous counts only)
    mood_by_type = defaultdict(int)
    for j in JournalEntry.query.all():
        mood_by_type[j.mood or 'Unspecified'] += 1
    mood_labels = list(mood_by_type.keys())
    mood_counts = [mood_by_type[m] for m in mood_labels]

    # 4. Breathing technique popularity
    tech_by_type = defaultdict(int)
    for b in BreathingSession.query.all():
        tech_by_type[b.technique] += 1
    tech_labels = list(tech_by_type.keys())
    tech_counts = [tech_by_type[t] for t in tech_labels]

    # 5. Average pre vs post score per dimension (effectiveness evidence)
    dims = ['stress_level', 'mood', 'sleep_quality', 'energy_level', 'anxiety_level']
    dim_labels = ['Stress', 'Mood', 'Sleep', 'Energy', 'Anxiety']
    pre_avgs, post_avgs = [], []
    pre_surveys = PreSurvey.query.all()
    post_surveys = PostSurvey.query.all()
    for d in dims:
        pre_vals = [getattr(p, d) for p in pre_surveys]
        post_vals = [getattr(p, d) for p in post_surveys]
        pre_avgs.append(round(sum(pre_vals) / len(pre_vals), 2) if pre_vals else 0)
        post_avgs.append(round(sum(post_vals) / len(post_vals), 2) if post_vals else 0)

    return render_template('admin-analytics.html',
                           reg_labels=reg_labels, reg_counts=reg_counts,
                           sess_labels=sess_labels, sess_counts=sess_counts,
                           mood_labels=mood_labels, mood_counts=mood_counts,
                           tech_labels=tech_labels, tech_counts=tech_counts,
                           dim_labels=dim_labels, pre_avgs=pre_avgs, post_avgs=post_avgs)

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    return render_template('500.html'), 500

# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == '__main__':
    # Run Flask development server
    # In production, use gunicorn or similar WSGI server
    # PORT is read from the environment so hosting platforms (and the
    # preview tool) can assign a port; defaults to 5000 for local use.
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)