# MindEase — AI-Powered Stress Management Chatbot

**Final Year Project by Shannon Fernandez (1211106748)**
**Supervisor: Dr Palanichamy Naveen**
Faculty of Computing and Informatics, Multimedia University

---

## Overview

MindEase is a web-based, AI-powered stress-management chatbot for university students and young adults. Unlike typical wellbeing chatbots, MindEase **measures the effectiveness of every session** by comparing a short assessment taken before and after each conversation, and it adapts its responses to the user's assessed stress level.

## Features

- **Stress-adaptive AI chat** powered by the Google Gemini API
- **Pre- and post-session assessment** across five dimensions (stress, mood, sleep, energy, anxiety)
- **Measured effectiveness** — a direction-aware before/after score with an improvement percentage
- **Crisis safety** — hard-coded crisis-keyword detection returns fixed local support resources before any AI call
- **Guided breathing exercise** with an animated pacer
- **Personal journal** with optional voice input (browser Web Speech API)
- **AI Wellness Insights** — privacy-preserving analysis of the user's own trends (never chat content)
- **Mood-adaptive motivational quotes**
- **Administration module** — user management, anonymous usage analytics, and quote management

## Technology Stack

**Backend:** Python 3.10 · Flask 3.1.3 · Flask-SQLAlchemy 3.1.1 · Flask-Login 0.6.3 · Werkzeug 3.1.8 · python-dotenv
**AI:** Google Gemini API accessed over REST, with a multi-model / multi-key fallback for reliability
**Frontend:** HTML5 · custom CSS3 (Flexbox & CSS Grid) · vanilla JavaScript · Jinja2 · Chart.js
**Database:** SQLite (development) · PostgreSQL-ready (production, via the `DATABASE_URL` variable)
**Server:** gunicorn (production WSGI)

## Project Structure

```
app.py            Routes and business logic
models.py         10 SQLAlchemy models + effectiveness calculation
gemini_api.py     Gemini integration, adaptive tone, crisis detection
config.py         Configuration (reads .env)
database.py       Database initialisation
templates/        Jinja2 HTML templates
static/           CSS and JavaScript
test_flow.py      Automated end-to-end test suite (43 checks)
requirements.txt  Python dependencies
```

## Setup

**Prerequisites:** Python 3.10+ and a Google Gemini API key (free from https://aistudio.google.com/app/apikey).

1. Create and activate a virtual environment, then install dependencies:
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows  (source venv/bin/activate on macOS/Linux)
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your values:
   ```
   SECRET_KEY=<a-long-random-string>
   GEMINI_API_KEY=<your-gemini-api-key>
   DATABASE_URL=sqlite:///instance/mindease.db
   ```

3. Run the application:
   ```bash
   python app.py
   ```

4. Open **http://127.0.0.1:5000** in your browser.

The database and a default administrator account are created automatically on first run.

## Default Accounts (development only)

| Role | Login | Credentials |
|------|-------|-------------|
| User | `/login` | `demo@mmu.edu.my` / `demo123` |
| Admin | `/admin/login` | `admin` / `AdminPass456` |

> These are development defaults for local testing and must be changed before any real deployment.

## Testing

Run the automated end-to-end test suite:
```bash
python -W ignore test_flow.py
```
This exercises every route and key behaviour (authentication, crisis detection, the effectiveness calculation, the admin module and the AI insights) and reports `43/43 checks passed`.

## Academic Note

MindEase was developed as a Final Year Project (FYP2) at Multimedia University. It is a **non-clinical** support tool and is **not a substitute for professional mental-health care**. In crisis, the app directs users to Befrienders Malaysia and campus counselling services.
