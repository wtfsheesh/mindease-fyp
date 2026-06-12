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
        
        # Seed motivational quotes
        print("Seeding motivational quotes...")
        quotes = [
            {
                'quote_text': 'Progress, not perfection. Something rather than nothing.',
                'author': 'Shannon',
                'is_active': True
            },
            {
                'quote_text': 'You are braver than you believe, stronger than you seem, and smarter than you think.',
                'author': 'A.A. Milne',
                'is_active': True
            },
            {
                'quote_text': 'The only way out is through.',
                'author': 'Robert Frost',
                'is_active': True
            },
            {
                'quote_text': 'You do not have to be good. You do not have to walk on your knees for a hundred miles through the desert, repenting. You only have to let the soft animal of your body love what it loves.',
                'author': 'Mary Oliver',
                'is_active': True
            },
            {
                'quote_text': 'Be kind to yourself. You are doing the best you can.',
                'author': 'Anonymous',
                'is_active': True
            },
            {
                'quote_text': 'Sometimes the smallest step in the right direction ends up being the biggest step of your life.',
                'author': 'Anonymous',
                'is_active': True
            },
            {
                'quote_text': 'It is okay to take a break. It is okay to ask for help. It is okay to not be okay.',
                'author': 'Anonymous',
                'is_active': True
            },
            {
                'quote_text': 'Your mental health is a priority. Your happiness is essential. Your self-care is a necessity.',
                'author': 'Anonymous',
                'is_active': True
            },
            {
                'quote_text': 'Healing is not linear. Some days will be better than others.',
                'author': 'Anonymous',
                'is_active': True
            },
            {
                'quote_text': 'You have survived 100% of your worst days. You are doing great.',
                'author': 'Anonymous',
                'is_active': True
            }
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