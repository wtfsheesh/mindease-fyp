# models.py
# Database models for MindEase
# Implements all 9 tables from FYP1 Report ERD
# Uses Flask-SQLAlchemy 3.1.1 as specified in report

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()

# ============================================================================
# TABLE 1: USER (Authentication and core user data)
# From FYP Report: Stores email and password_hash
# ============================================================================

class User(UserMixin, db.Model):
    """
    User model for authentication
    Corresponds to 'User' table in ERD
    """
    __tablename__ = 'user'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # User Credentials
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships (One-to-Many)
    profile = db.relationship('Profile', backref='user', uselist=False, cascade='all, delete-orphan')
    chat_sessions = db.relationship('ChatSession', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    journal_entries = db.relationship('JournalEntry', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    breathing_sessions = db.relationship('BreathingSession', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """
        Hash password using Werkzeug (as specified in FYP report)
        Security: Passwords never stored as plain text
        """
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """
        Verify password against hash
        Returns: True if password matches, False otherwise
        """
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'


# ============================================================================
# TABLE 2: PROFILE (Optional user demographics)
# From FYP Report: Optional name and age_group
# ============================================================================

class Profile(db.Model):
    """
    Profile model for optional user information
    Corresponds to 'Profile' table in ERD
    """
    __tablename__ = 'profile'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Profile Data (Optional)
    name = db.Column(db.String(100), nullable=True)
    age_group = db.Column(db.String(20), nullable=True)  # 18-24, 25-34, etc.
    
    def __repr__(self):
        return f'<Profile {self.name}>'


# ============================================================================
# TABLE 3: CHAT SESSION (Tracks each conversation session)
# From FYP Report: Stores session metadata and stress level
# ============================================================================

class ChatSession(db.Model):
    """
    ChatSession model for tracking chat conversations
    Corresponds to 'ChatSession' table in ERD
    """
    __tablename__ = 'chat_session'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Session Metadata
    start_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    initial_stress_level = db.Column(db.Integer, nullable=True)  # From pre-assessment
    
    # Relationships (One-to-Many and One-to-One)
    messages = db.relationship('ChatMessage', backref='session', lazy='dynamic', cascade='all, delete-orphan')
    pre_survey = db.relationship('PreSurvey', backref='session', uselist=False, cascade='all, delete-orphan')
    post_survey = db.relationship('PostSurvey', backref='session', uselist=False, cascade='all, delete-orphan')
    
    def get_duration_minutes(self):
        """Calculate session duration in minutes"""
        if self.end_time and self.start_time:
            duration = self.end_time - self.start_time
            return int(duration.total_seconds() / 60)
        return 0
    
    def get_message_count(self):
        """Get total number of messages in session"""
        return self.messages.count()
    
    def __repr__(self):
        return f'<ChatSession {self.id} - User {self.user_id}>'


# ============================================================================
# TABLE 4: CHAT MESSAGE (Individual messages in conversation)
# From FYP Report: Stores all conversation exchanges
# ============================================================================

class ChatMessage(db.Model):
    """
    ChatMessage model for storing individual messages
    Corresponds to 'ChatMessage' table in ERD
    """
    __tablename__ = 'chat_message'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)
    
    # Message Data
    sender = db.Column(db.String(10), nullable=False)  # 'user' or 'bot'
    message_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<ChatMessage {self.id} from {self.sender}>'


# ============================================================================
# TABLE 5: PRE SURVEY (Before-session assessment)
# From FYP Report: 5 dimensions - stress, mood, sleep, energy, anxiety
# ============================================================================

class PreSurvey(db.Model):
    """
    PreSurvey model for pre-session stress assessment
    Corresponds to 'PreSurvey' table in ERD
    Stores 5 dimensions as specified in FYP report
    """
    __tablename__ = 'pre_survey'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key (One-to-One with ChatSession)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False, unique=True)
    
    # 5 Assessment Dimensions (1-5 scale)
    stress_level = db.Column(db.Integer, nullable=False)  # 1=Very Low, 5=Very High
    mood = db.Column(db.Integer, nullable=False)          # 1=Very Low, 5=Very High
    sleep_quality = db.Column(db.Integer, nullable=False) # 1=Very Poor, 5=Very Good
    energy_level = db.Column(db.Integer, nullable=False)  # 1=Very Low, 5=Very High
    anxiety_level = db.Column(db.Integer, nullable=False) # 1=Very Low, 5=Very High
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def get_total_score(self):
        """
        Calculate total score (sum of all dimensions)
        Used for overall effectiveness calculation
        """
        return (self.stress_level + self.mood + self.sleep_quality + 
                self.energy_level + self.anxiety_level)
    
    def __repr__(self):
        return f'<PreSurvey Session {self.session_id}>'


# ============================================================================
# TABLE 6: POST SURVEY (After-session assessment)
# From FYP Report: Same 5 dimensions for comparison
# ============================================================================

class PostSurvey(db.Model):
    """
    PostSurvey model for post-session stress assessment
    Corresponds to 'PostSurvey' table in ERD
    Same structure as PreSurvey for comparison
    """
    __tablename__ = 'post_survey'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key (One-to-One with ChatSession)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False, unique=True)
    
    # 5 Assessment Dimensions (1-5 scale)
    stress_level = db.Column(db.Integer, nullable=False)
    mood = db.Column(db.Integer, nullable=False)
    sleep_quality = db.Column(db.Integer, nullable=False)
    energy_level = db.Column(db.Integer, nullable=False)
    anxiety_level = db.Column(db.Integer, nullable=False)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def get_total_score(self):
        """Calculate total score"""
        return (self.stress_level + self.mood + self.sleep_quality + 
                self.energy_level + self.anxiety_level)
    
    def __repr__(self):
        return f'<PostSurvey Session {self.session_id}>'


# ============================================================================
# TABLE 7: JOURNAL ENTRY (Personal reflection entries)
# From FYP Report: Title, content, mood tracking
# ============================================================================

class JournalEntry(db.Model):
    """
    JournalEntry model for personal journaling
    Corresponds to 'JournalEntry' table in ERD
    """
    __tablename__ = 'journal_entry'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Journal Data
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(20), nullable=True)  # Happy, Calm, Stressed, Sad, Anxious, Neutral
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<JournalEntry {self.title}>'


# ============================================================================
# TABLE 8: BREATHING SESSION (Breathing exercise tracking)
# From FYP Report: Track breathing exercise completions
# ============================================================================

class BreathingSession(db.Model):
    """
    BreathingSession model for tracking breathing exercises
    Corresponds to 'BreathingSession' table in ERD
    """
    __tablename__ = 'breathing_session'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Breathing Exercise Data
    technique = db.Column(db.String(50), nullable=False)  # Box, Deep, 4-7-8
    completed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<BreathingSession {self.technique}>'


# ============================================================================
# TABLE 9: DAILY MOTIVATION (Motivational quotes)
# From FYP Report: Admin-managed inspirational quotes
# ============================================================================

class DailyMotivation(db.Model):
    """
    DailyMotivation model for motivational quotes
    Corresponds to 'DailyMotivation' table in ERD
    """
    __tablename__ = 'daily_motivation'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Quote Data
    quote_text = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<DailyMotivation by {self.author}>'


# ============================================================================
# HELPER FUNCTIONS FOR EFFECTIVENESS CALCULATION
# From FYP Report: Calculate improvement percentages
# ============================================================================

def calculate_effectiveness(session_id):
    """
    Calculate effectiveness of a chat session
    Compares PreSurvey and PostSurvey scores
    
    Returns dict with:
    - overall_improvement: percentage
    - dimension_changes: dict of individual dimension changes
    - effectiveness_status: 'IMPROVED' or 'NO CHANGE'
    """
    session = ChatSession.query.get(session_id)
    
    if not session or not session.pre_survey or not session.post_survey:
        return None
    
    pre = session.pre_survey
    post = session.post_survey

    # Calculate direction-aware distress scores (lower = better).
    # Stress and anxiety are already "lower is better"; mood, sleep and
    # energy are "higher is better" so they are inverted (6 - value).
    # Without this, an improvement in mood/sleep/energy would cancel out
    # a reduction in stress/anxiety and report NO CHANGE for a good session.
    def distress_score(survey):
        return (survey.stress_level + survey.anxiety_level +
                (6 - survey.mood) + (6 - survey.sleep_quality) +
                (6 - survey.energy_level))

    pre_total = distress_score(pre)
    post_total = distress_score(post)

    # Overall improvement percentage: (pre - post) / pre * 100
    if pre_total > 0:
        overall_improvement = ((pre_total - post_total) / pre_total) * 100
    else:
        overall_improvement = 0
    
    # Calculate individual dimension changes
    dimension_changes = {
        'stress': {
            'before': pre.stress_level,
            'after': post.stress_level,
            'change': pre.stress_level - post.stress_level,
            'percentage': ((pre.stress_level - post.stress_level) / pre.stress_level * 100) if pre.stress_level > 0 else 0
        },
        'mood': {
            'before': pre.mood,
            'after': post.mood,
            'change': post.mood - pre.mood,  # Positive change is good for mood
            'percentage': ((post.mood - pre.mood) / pre.mood * 100) if pre.mood > 0 else 0
        },
        'sleep': {
            'before': pre.sleep_quality,
            'after': post.sleep_quality,
            'change': post.sleep_quality - pre.sleep_quality,
            'percentage': ((post.sleep_quality - pre.sleep_quality) / pre.sleep_quality * 100) if pre.sleep_quality > 0 else 0
        },
        'energy': {
            'before': pre.energy_level,
            'after': post.energy_level,
            'change': post.energy_level - pre.energy_level,
            'percentage': ((post.energy_level - pre.energy_level) / pre.energy_level * 100) if pre.energy_level > 0 else 0
        },
        'anxiety': {
            'before': pre.anxiety_level,
            'after': post.anxiety_level,
            'change': pre.anxiety_level - post.anxiety_level,
            'percentage': ((pre.anxiety_level - post.anxiety_level) / pre.anxiety_level * 100) if pre.anxiety_level > 0 else 0
        }
    }
    
    # Determine effectiveness status
    effectiveness_status = 'IMPROVED' if overall_improvement > 0 else 'NO CHANGE'
    
    return {
        'pre_total': pre_total,
        'post_total': post_total,
        'overall_improvement': round(overall_improvement, 1),
        'dimension_changes': dimension_changes,
        'effectiveness_status': effectiveness_status
    }