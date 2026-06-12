# app.py
# Main Flask Application for MindEase
# Implements all routes and functionality from FYP1 report
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
from models import db, User, Profile, ChatSession, ChatMessage, PreSurvey, PostSurvey, JournalEntry, BreathingSession, DailyMotivation, calculate_effectiveness

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

# ============================================================================
# ROUTE 1: HOME / LOGIN PAGE
# ============================================================================

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

# ============================================================================
# ROUTE 2: REGISTRATION
# ============================================================================

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

# ============================================================================
# ROUTE 3: DASHBOARD
# ============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    """
    Dashboard - main hub showing statistics and quick actions
    Implements dashboard features from FYP report
    """
    # Get user statistics
    total_sessions = ChatSession.query.filter_by(user_id=current_user.id).count()
    
    # Calculate average stress reduction
    completed_sessions = ChatSession.query.filter_by(user_id=current_user.id).filter(
        ChatSession.end_time.isnot(None)
    ).all()
    
    stress_reductions = []
    for session in completed_sessions:
        effectiveness = calculate_effectiveness(session.id)
        if effectiveness and effectiveness['overall_improvement'] > 0:
            stress_reductions.append(effectiveness['overall_improvement'])
    
    avg_stress_reduction = round(sum(stress_reductions) / len(stress_reductions)) if stress_reductions else 0
    
    # Get total journal entries
    total_journals = JournalEntry.query.filter_by(user_id=current_user.id).count()
    
    # Get random motivational quote
    active_quotes = DailyMotivation.query.filter_by(is_active=True).all()
    if active_quotes:
        daily_quote = random.choice(active_quotes)
    else:
        daily_quote = None
    
    # Get user name for welcome message
    user_name = current_user.email.split('@')[0]  # Default to email prefix
    if current_user.profile and current_user.profile.name:
        user_name = current_user.profile.name
    
    return render_template('dashboard.html',
                         user_name=user_name,
                         total_sessions=total_sessions,
                         avg_stress_reduction=avg_stress_reduction,
                         total_journals=total_journals,
                         daily_quote=daily_quote)

# ============================================================================
# ROUTE 4: PRE-SESSION ASSESSMENT
# ============================================================================

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

# ============================================================================
# ROUTE 7: END SESSION
# ============================================================================

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

# ============================================================================
# ROUTE 8: POST-SESSION ASSESSMENT
# ============================================================================

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

# ============================================================================
# ROUTE 9: COMPARISON / RESULTS
# ============================================================================

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
    
    # Calculate effectiveness
    effectiveness = calculate_effectiveness(session_id)
    
    if not effectiveness:
        flash('Cannot calculate effectiveness. Assessment data missing.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('comparison.html',
                         session=chat_session,
                         effectiveness=effectiveness)

# ============================================================================
# ROUTE 10: SESSION HISTORY
# ============================================================================

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

# ============================================================================
# ROUTE 11: BREATHING EXERCISES
# ============================================================================

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

# ============================================================================
# ROUTE 12: JOURNAL
# ============================================================================

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
    app.run(debug=True, host='0.0.0.0', port=5000)