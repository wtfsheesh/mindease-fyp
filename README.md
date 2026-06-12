# MindEase - AI-Powered Stress Management Chatbot

**FYP Project by Shannon Fernandez (1211106748)**  
**Supervised by Dr. Palanichammy Naveen**

## Description

MindEase is an AI-powered stress management chatbot designed for university students aged 18-35. It provides:
- Adaptive AI conversations using Google Gemini API
- Pre/post-session stress assessments (5 dimensions)
- Effectiveness measurement and tracking
- Breathing exercises and journaling tools
- Privacy-first design with optional anonymous access

## Technology Stack

**Backend:**
- Python 3.10.8
- Flask 3.0.0
- Flask-SQLAlchemy 3.1.1
- Google Gemini API (google-generativeai 0.3.1)
- Werkzeug (password hashing)

**Frontend:**
- HTML5
- CSS3
- JavaScript ES6
- Bootstrap 5.0

**Database:**
- SQLite 3.40 (development)
- PostgreSQL 13+ (production)

## Installation

### Prerequisites
- Python 3.10 or higher
- Google Gemini API key (free from https://makersuite.google.com/app/apikey)

### Setup Steps

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment variables:**
Create a `.env` file with: