# database.py
# Database initialization script for MindEase
# Creates all tables and seeds initial data

from app import app, db
from models import DailyMotivation

def init_database():
    """
    Initialize database with tables and seed data
    Run this once before first use
    """
    with app.app_context():
        # Drop all existing tables (WARNING: deletes all data!)
        print("Dropping existing tables...")
        db.drop_all()
        
        # Create all tables from models
        print("Creating database tables...")
        db.create_all()
        
        # Seed motivational quotes (with emotion categories for mood-adaptive display)
        print("Seeding motivational quotes...")
        quotes = [
            # General quotes (shown for Neutral mood or as a fallback)
            {'quote_text': 'Progress, not perfection. Something rather than nothing.', 'author': 'Shannon', 'is_active': True, 'emotion': 'general'},
            {'quote_text': 'You are braver than you believe, stronger than you seem, and smarter than you think.', 'author': 'A.A. Milne', 'is_active': True, 'emotion': 'general'},
            {'quote_text': 'The only way out is through.', 'author': 'Robert Frost', 'is_active': True, 'emotion': 'general'},
            {'quote_text': 'Be kind to yourself. You are doing the best you can.', 'author': 'Anonymous', 'is_active': True, 'emotion': 'general'},
            {'quote_text': 'Healing is not linear. Some days will be better than others.', 'author': 'Anonymous', 'is_active': True, 'emotion': 'general'},
            {'quote_text': 'You have survived 100% of your worst days. You are doing great.', 'author': 'Anonymous', 'is_active': True, 'emotion': 'general'},
            # Happy
            {'quote_text': 'Happiness is not something ready made. It comes from your own actions.', 'author': 'Dalai Lama', 'is_active': True, 'emotion': 'Happy'},
            {'quote_text': 'Celebrate the small wins; they add up to big victories.', 'author': 'Anonymous', 'is_active': True, 'emotion': 'Happy'},
            # Calm
            {'quote_text': 'Within you there is a stillness and a sanctuary to which you can retreat at any time.', 'author': 'Hermann Hesse', 'is_active': True, 'emotion': 'Calm'},
            {'quote_text': 'Calm mind brings inner strength and self-confidence.', 'author': 'Dalai Lama', 'is_active': True, 'emotion': 'Calm'},
            # Stressed
            {'quote_text': 'You do not have to control your thoughts. You just have to stop letting them control you.', 'author': 'Dan Millman', 'is_active': True, 'emotion': 'Stressed'},
            {'quote_text': 'Almost everything will work again if you unplug it for a few minutes, including you.', 'author': 'Anne Lamott', 'is_active': True, 'emotion': 'Stressed'},
            # Sad
            {'quote_text': 'Even the darkest night will end and the sun will rise.', 'author': 'Victor Hugo', 'is_active': True, 'emotion': 'Sad'},
            {'quote_text': "Your present circumstances don't determine where you can go; they merely determine where you start.", 'author': 'Nido Qubein', 'is_active': True, 'emotion': 'Sad'},
            # Anxious
            {'quote_text': "You don't have to see the whole staircase, just take the first step.", 'author': 'Martin Luther King Jr.', 'is_active': True, 'emotion': 'Anxious'},
            {'quote_text': 'Nothing diminishes anxiety faster than action.', 'author': 'Walter Anderson', 'is_active': True, 'emotion': 'Anxious'},
        ]
        
        for quote_data in quotes:
            quote = DailyMotivation(**quote_data)
            db.session.add(quote)
        
        db.session.commit()
        
        print("\n✅ Database initialized successfully!")
        print(f"✅ Created {len(quotes)} motivational quotes")
        print("\nYou can now run the application with: python app.py")

if __name__ == '__main__':
    print("=== MindEase Database Initialization ===\n")
    response = input("This will DELETE all existing data. Continue? (yes/no): ")
    
    if response.lower() == 'yes':
        init_database()
    else:
        print("Database initialization cancelled.")