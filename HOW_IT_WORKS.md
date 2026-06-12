# MindEase — Complete A-to-Z Guide to How the Application Works

> Written for Shannon Fernandez. This explains every part of MindEase as if you
> are learning it for the first time. Read it top to bottom once, then use it
> as a reference when preparing for your demo and viva.

---

## Part 1: The Big Picture

### What kind of application is this?

MindEase is a **web application**. That means:
- The user opens a **browser** (Chrome, Edge) and types an address (`http://localhost:5000`)
- The browser sends a **request** to a **server** (your Python program)
- The server sends back **HTML** (a web page) which the browser displays

Your Python program (`app.py`) IS the server. When you run `python app.py`,
your computer starts listening on **port 5000** for browser requests.

### The three layers (Three-Tier Architecture from your FYP1 report)

```
┌─────────────────────────────────────────────┐
│  PRESENTATION LAYER (what the user sees)    │
│  HTML templates + CSS styles + JavaScript   │
│  Files: templates/*.html, static/css, js    │
└──────────────────┬──────────────────────────┘
                   │ HTTP requests/responses
┌──────────────────▼──────────────────────────┐
│  APPLICATION LAYER (the brain)              │
│  Flask routes, business logic, Gemini AI    │
│  Files: app.py, gemini_api.py, config.py    │
└──────────────────┬──────────────────────────┘
                   │ SQL queries (via SQLAlchemy)
┌──────────────────▼──────────────────────────┐
│  DATA LAYER (where everything is stored)    │
│  SQLite database file                       │
│  Files: models.py, instance/mindease.db     │
└─────────────────────────────────────────────┘
```

**Why three layers?** Separation of concerns. The HTML doesn't know SQL exists.
The database doesn't know what a web page is. Each layer only talks to the
layer next to it. If you swap SQLite for PostgreSQL later, only the data layer
changes.

### Every file and what it does

| File | Role | One-line description |
|------|------|---------------------|
| `app.py` | Application layer | The server. Defines all 14 routes (URLs) and what happens when each is visited |
| `models.py` | Data layer | Defines the 9 database tables as Python classes, plus the effectiveness calculation |
| `gemini_api.py` | Application layer | Talks to Google's Gemini AI. Builds prompts, detects crisis keywords |
| `config.py` | Configuration | Settings: secret key, database location, session lifetime |
| `database.py` | Setup script | Run once to create tables and insert the 10 motivational quotes |
| `.env` | Secrets | Your API key and secret key. NEVER committed to git |
| `requirements.txt` | Dependencies | List of Python packages the app needs |
| `templates/*.html` | Presentation | 13 Jinja2 templates — the web pages |
| `static/css/styles.css` | Presentation | All the visual styling |
| `static/js/script.js` | Presentation | Global JavaScript helpers |
| `instance/mindease.db` | Data | The actual SQLite database file (auto-created) |
| `test_flow.py` | Testing | Automated test of the entire user journey (22 checks) |

---

## Part 2: What Happens When You Run `python app.py`

Step by step, in order:

1. **`load_dotenv()`** reads your `.env` file and puts `SECRET_KEY`,
   `GEMINI_API_KEY`, and `DATABASE_URL` into the program's environment
   variables, so other code can read them with `os.getenv()`.

2. **Imports run.** `from models import db, User, ...` loads your table
   definitions. `from gemini_api import create_chatbot` loads the AI code.

3. **`app = Flask(__name__)`** creates the Flask application object. Think of
   it as creating an empty switchboard with no phone lines connected yet.

4. **`app.config.from_object(Config)`** loads the settings from `config.py`
   (secret key, database URI, session lifetime).

5. **`db.init_app(app)`** connects SQLAlchemy (the database toolkit) to Flask.

6. **`login_manager.init_app(app)`** connects Flask-Login, which manages "who
   is currently logged in".

7. **`db.create_all()`** looks at all 9 model classes and creates their tables
   in `instance/mindease.db` if they don't already exist.

8. **`chatbot = create_chatbot()`** creates the GeminiChatbot object, ready to
   call the AI. If this fails (no API key), the app still runs — the bot just
   uses fallback messages.

9. **All the `@app.route(...)` decorators register the 14 routes.** This is
   the switchboard getting its phone lines: "/login goes to the login()
   function", "/chat goes to the chat() function", etc.

10. **`app.run(debug=True, port=5000)`** starts the web server. Now the app
    sits and waits for browsers to connect.

---

## Part 3: Core Concepts You Must Understand

### 3.1 What is a route?

A route maps a **URL** to a **Python function**. When a browser requests that
URL, Flask runs the function and sends back whatever it returns.

```python
@app.route('/dashboard')      # ← "when someone visits /dashboard..."
@login_required               # ← "...but only if they are logged in..."
def dashboard():              # ← "...run this function"
    ...
    return render_template('dashboard.html', ...)   # ← send back this page
```

### 3.2 GET vs POST

- **GET** = "give me a page". Typing a URL or clicking a link is a GET.
- **POST** = "here is data, process it". Submitting a form is a POST.

A route like `@app.route('/login', methods=['GET', 'POST'])` handles both:
GET shows the login form; POST receives the submitted email/password.
Inside the function, `if request.method == 'POST':` separates the two cases.

### 3.3 What is a template? (Jinja2)

A template is an HTML file with **placeholders**. Flask fills the placeholders
with real data before sending the page to the browser.

```html
<h2>Welcome, {{ user_name }}!</h2>        ← variable inserted here
{% if messages %} ... {% endif %}          ← logic (if/for) in the template
{% extends "base.html" %}                  ← inherit a shared page skeleton
```

`render_template('dashboard.html', user_name='Shannon')` → Flask opens the
file, replaces `{{ user_name }}` with "Shannon", and returns finished HTML.

### 3.4 What is a model? (SQLAlchemy ORM)

An ORM (Object-Relational Mapper) lets you use **Python classes instead of SQL**.

```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
```

This class IS the `user` table. Each User **object** is one **row**.

| You write (Python) | SQLAlchemy runs (SQL) |
|---|---|
| `User.query.filter_by(email=e).first()` | `SELECT * FROM user WHERE email=? LIMIT 1` |
| `db.session.add(new_user)` then `commit()` | `INSERT INTO user (...) VALUES (...)` |
| `db.session.delete(user)` then `commit()` | `DELETE FROM user WHERE id=?` |

`db.session` is a "shopping cart" of pending changes. Nothing touches the
database until `db.session.commit()`. If something goes wrong,
`db.session.rollback()` empties the cart safely.

### 3.5 What is a session? (two different meanings — important!)

This trips everyone up. MindEase uses the word "session" for TWO things:

1. **Flask session** (`from flask import session`) — a small encrypted cookie
   stored in the browser that remembers data between page loads. We use it to
   remember which chat the user is currently in:
   `session['current_session_id'] = 5`. It is signed with your SECRET_KEY so
   users can't tamper with it.

2. **ChatSession** (the database table) — one record per conversation, with
   start time, end time, and stress level.

So: "Flask session" = browser memory. "ChatSession" = a row in the database.

### 3.6 How login works (Flask-Login + password hashing)

**Passwords are never stored.** When a user registers:

```python
new_user.set_password("mypassword123")
# internally: generate_password_hash() → "scrypt:32768:8:1$Kj2...xyz"
```

A **hash** is a one-way scramble. You cannot reverse it to get the password
back. At login, `check_password()` hashes what the user typed and compares the
two hashes. Even if someone steals the database, they can't read passwords.

**Flask-Login** then keeps the user logged in:
- `login_user(user)` → writes the user's ID into the signed session cookie
- On every later request, the `@login_manager.user_loader` function runs:
  `load_user(user_id)` fetches the User from the database
- `current_user` then refers to that User everywhere in your code
- `@login_required` blocks the route and redirects to login if nobody is
  logged in
- `logout_user()` erases the cookie

### 3.7 Database relationships (how tables connect)

```
User ──1:1── Profile                 (one user, one optional profile)
User ──1:M── ChatSession             (one user, many chat sessions)
User ──1:M── JournalEntry
User ──1:M── BreathingSession
ChatSession ──1:M── ChatMessage      (one conversation, many messages)
ChatSession ──1:1── PreSurvey        (one assessment before)
ChatSession ──1:1── PostSurvey       (one assessment after)
DailyMotivation                      (standalone — not linked to users)
```

A relationship needs two pieces:

1. **Foreign key** — the actual column in the table:
   `user_id = db.Column(db.Integer, db.ForeignKey('user.id'))`
   ("each chat session row stores WHICH user owns it")

2. **relationship()** — the Python convenience that lets you hop between
   objects without writing queries:
   `chat_sessions = db.relationship('ChatSession', backref='user', ...)`
   Now `user.chat_sessions` gives the list of sessions, and (because of
   `backref`) `some_session.user` gives the owner.

**1:1 vs 1:M:** `uselist=False` on the relationship makes it one-to-one
(profile, pre_survey, post_survey). `unique=True` on the foreign key enforces
it at the database level — a session can never have two pre-surveys.

**`cascade='all, delete-orphan'`** means: delete a user → all their sessions,
messages, journals are automatically deleted too. No orphan data.

---

## Part 4: The Complete User Journey, Step by Step

This is the heart of the guide. Follow one user, "Aina", through the entire app.

### Step 1: Registration (`/register`)

1. Aina's browser GETs `/register` → Flask returns `register.html` (the form).
2. She fills email, password, confirm password, name, age group and clicks
   Register → browser POSTs the form data to `/register`.
3. The `register()` function in app.py:
   - Reads the fields: `request.form.get('email')` etc.
   - **Validates**: both fields present? passwords match? at least 8 chars?
   - **Checks duplicates**: `User.query.filter_by(email=email).first()` —
     if found, flash an error.
   - Creates `User(email=...)`, calls `set_password()` (hashing happens here),
     `db.session.add()`, `db.session.commit()` → the row now exists.
   - If she gave a name/age group, also creates a `Profile` row pointing at
     her user id.
   - `flash('Registration successful!...')` queues a one-time message, and
     `redirect(url_for('login'))` sends her to the login page, where the
     green flash message is displayed.

**What is flash?** A message stored in the session cookie that survives ONE
redirect and is then deleted. That's how "Registration successful!" appears on
a *different* page than the one that created it.

### Step 2: Login (`/login`)

1. Browser POSTs email + password.
2. `login()`:
   - Finds the user: `User.query.filter_by(email=email).first()`
   - `user.check_password(password)` — hashes the attempt, compares
   - Success → `login_user(user, remember=True)` writes the signed cookie
   - `redirect(url_for('dashboard'))`
3. From now on, every request Aina makes carries that cookie, and Flask-Login
   turns it back into `current_user` automatically.

### Step 3: Dashboard (`/dashboard`)

The `dashboard()` function gathers four pieces of data and hands them to the
template:

1. **Total sessions**: `ChatSession.query.filter_by(user_id=current_user.id).count()`
2. **Average stress reduction**: loops over completed sessions, calls
   `calculate_effectiveness()` for each, averages the positive improvements
3. **Journal count**: same idea with `JournalEntry`
4. **Random quote**: picks one active row from `DailyMotivation`

`render_template('dashboard.html', user_name=..., total_sessions=..., ...)`
fills the placeholders and the browser shows her stats.

### Step 4: Pre-Assessment (`/pre-assessment`)

Aina clicks "Start New Session".

1. GET shows the form: 5 questions (stress, mood, sleep, energy, anxiety),
   each a row of radio buttons 1–5.
2. She picks her answers and submits → POST.
3. `pre_assessment()`:
   - Reads the 5 values, validates each is between 1 and 5
   - Creates a **ChatSession** row (`initial_stress_level=stress`)
   - `db.session.flush()` — this is subtle: flush sends the INSERT to the
     database *without* committing, just so the new session gets its **id**
     (the database assigns ids). We need that id for the next step.
   - Creates a **PreSurvey** row with `session_id=new_session.id`
   - `db.session.commit()` — now both rows are saved together
   - **`session['current_session_id'] = new_session.id`** — remembers in the
     browser cookie which conversation is active
   - Redirects to `/chat`

### Step 5: The Chat Page Loads (`/chat`)

1. `chat()` reads `session.get('current_session_id')` from the cookie.
   No id? → redirect back to pre-assessment ("No active session").
2. **Security check**: loads the ChatSession and verifies
   `chat_session.user_id == current_user.id` — Aina can't open someone
   else's conversation by guessing ids.
3. Already ended (`end_time` set)? → redirect away. Old sessions are read-only.
4. Loads all messages: `ChatMessage.query.filter_by(session_id=...).order_by(timestamp)`
5. **First visit special case**: zero messages → the bot speaks first.
   `chatbot.get_conversation_starter(stress_level)` returns one of three
   greetings depending on her stress level (4–5 calm/reassuring, 3 supportive,
   1–2 encouraging). That message is saved as a ChatMessage with
   `sender='bot'` and shown.
6. The template renders all messages in bubbles, plus the input box. Crucially
   it embeds: `const SESSION_ID = {{ session_id }};` — JavaScript on the page
   now knows which session it belongs to.

### Step 6: Sending a Message (the AJAX flow — the most important part)

**What is AJAX?** Normally, submitting a form reloads the whole page. AJAX
(JavaScript `fetch()`) sends data to the server *in the background* and
updates only part of the page. That's why chat feels like WhatsApp, not like
filling forms.

The full round trip when Aina types "I'm stressed about exams" and hits Send:

```
BROWSER (JavaScript in chat.html)              SERVER (app.py + gemini_api.py)
─────────────────────────────────              ────────────────────────────────
1. sendMessage() runs
2. Disables input, shows her bubble
   immediately (optimistic UI)
3. Shows typing indicator (3 dots)
4. fetch('/api/send-message', {
     method: 'POST',
     body: JSON {message, session_id}
   })                              ──────────► 5. send_message() runs:
                                                  - validates message + session
                                                  - checks session belongs to her
                                                  - checks session not ended
                                               6. Saves HER message to DB
                                                  (ChatMessage, sender='user')
                                               7. Loads last 10 messages as
                                                  conversation_history
                                               8. chatbot.generate_response(...)
                                                  ┌──────────────────────────┐
                                                  │ a. Crisis keyword check  │
                                                  │    (BEFORE any AI call)  │
                                                  │ b. Build adaptive prompt │
                                                  │ c. POST to Google Gemini │
                                                  │    (2.5-flash, fallback  │
                                                  │    to 2.0-flash, lite)   │
                                                  │ d. Extract reply text    │
                                                  └──────────────────────────┘
                                               9. Saves BOT message to DB
                                                  (ChatMessage, sender='bot')
                                  ◄────────── 10. Returns JSON:
                                                  {success: true,
                                                   bot_message: "..."}
11. Removes typing indicator
12. Adds bot bubble to the page
13. Re-enables input
```

No page reload ever happens. Steps 5–10 take 1–7 seconds (that's the Gemini
API call) — which is exactly why the typing indicator exists.

**escapeHtml():** before inserting any text into the page, the JavaScript
escapes it so `<script>` typed by a user becomes harmless text, not running
code. This prevents XSS (cross-site scripting) attacks.

### Step 7: Inside `gemini_api.py` — how the AI actually gets called

`generate_response(user_message, stress_level, conversation_history)` does:

1. **Crisis detection FIRST** — `detect_crisis_keywords()` scans for phrases
   like "kill myself", "end it all". If found, the function returns the
   hardcoded crisis response (Befrienders 03-7956-8145, Emergency 999, MMU
   Counseling) **immediately — Gemini is never called**. Design decision:
   never trust an AI with a life-or-death response.

2. **Build the adaptive prompt.** Based on `stress_level`:
   - 4–5 → "Use a calm, reassuring tone, offer grounding techniques..."
   - 3 → "Be supportive and solution-focused..."
   - 1–2 → "Be positive and encouraging, build resilience..."
   This instruction + the last 10 messages + the new message are combined into
   one text prompt. The history is what makes the bot remember the
   conversation — Gemini itself is stateless; *we* re-send the context every
   time.

3. **Call the API.** A JSON payload
   `{"contents":[{"parts":[{"text": prompt}]}], "generationConfig": {...}}`
   is POSTed over HTTPS to
   `https://generativelanguage.googleapis.com/v1beta/models/<model>:generateContent?key=API_KEY`
   using Python's built-in `urllib`. Temperature 0.7 = moderately creative.

4. **Model fallback.** Free-tier quotas are *per model*. The code tries
   `gemini-2.5-flash` first; on HTTP 429 (rate limit) it tries
   `gemini-2.0-flash`, then `gemini-2.0-flash-lite`. Only if all three fail
   does it return the safe fallback sentence ("I am right here listening...").
   The app therefore never crashes from API problems.

5. **Parse the response.** Gemini returns JSON; the reply text lives at
   `response_data['candidates'][0]['content']['parts'][0]['text']`.

### Step 8: Ending the Session (`/end-session/<id>`)

Aina clicks "End Session" → a JavaScript `confirm()` dialog → a hidden form
POSTs to `/end-session/5`. The route verifies ownership, sets
`end_time = datetime.utcnow()`, commits, and redirects to `/post-assessment`.
Once `end_time` is set, the chat page and the send-message API both refuse
this session — it's frozen forever.

### Step 9: Post-Assessment (`/post-assessment`)

Identical form to the pre-assessment (same 5 questions — deliberately, so the
before/after comparison is apples-to-apples). The route also checks
`if chat_session.post_survey:` to block double submission (the 1:1
relationship + unique constraint guarantee it in the database too). Saves the
PostSurvey, redirects to `/comparison/5`.

### Step 10: The Effectiveness Calculation (the academic core of your FYP)

`calculate_effectiveness(session_id)` in models.py:

**The direction problem:** for stress and anxiety, going DOWN is good. For
mood, sleep, energy, going UP is good. You cannot just add raw scores —
improvements would cancel each other out. (This was a real bug we found in
testing: a session where every dimension improved reported "NO CHANGE".)

**The solution — a unified distress score** where lower always = better:

```
distress = stress + anxiety + (6−mood) + (6−sleep) + (6−energy)
```

The `(6−x)` flips the positive dimensions: mood 5 (great) becomes 1 (low
distress), mood 1 (awful) becomes 5 (high distress). Range: 5–25.

**Worked example (Aina):**

| Dimension | Pre | Post | Pre distress | Post distress |
|-----------|-----|------|--------------|---------------|
| Stress    | 4   | 2    | 4            | 2             |
| Anxiety   | 4   | 2    | 4            | 2             |
| Mood      | 2   | 4    | 6−2 = 4      | 6−4 = 2       |
| Sleep     | 2   | 3    | 6−2 = 4      | 6−3 = 3       |
| Energy    | 2   | 4    | 6−2 = 4      | 6−4 = 2       |
| **Total** |     |      | **20**       | **11**        |

```
improvement = (pre − post) / pre × 100 = (20 − 11) / 20 × 100 = 45%
status = 'IMPROVED'  (because improvement > 0)
```

The function also returns per-dimension changes (before, after, change,
percentage — direction-aware), which the comparison page shows as the
color-coded table with ↓/↑ arrows.

### Step 11: History, Breathing, Journal

- **`/history`**: all sessions with an `end_time`, newest first, each with its
  effectiveness, duration (`end_time − start_time`), and message count.
- **`/breathing`**: a static page; the three techniques (Box, Deep, 4-7-8) are
  a JavaScript object in the template, animated client-side. When Aina
  completes one, JS POSTs to `/api/complete-breathing` which inserts a
  BreathingSession row — same AJAX pattern as chat, simpler payload.
- **`/journal`**: classic form POST. Title + content required, mood optional
  (one of Happy/Calm/Stressed/Sad/Anxious/Neutral). Saves a JournalEntry.

### Step 12: Logout

`logout_user()` clears the cookie, flash "You have been logged out", redirect
to `/`. Visiting `/dashboard` now bounces to the login page because of
`@login_required`.

---

## Part 5: Security — Every Protection in the App

| Threat | Protection | Where |
|--------|-----------|-------|
| Stolen password database | Werkzeug one-way hashing — plaintext never stored | `models.py` set_password |
| Accessing pages without login | `@login_required` on every private route | `app.py` |
| Opening another user's session/data | Ownership check `user_id == current_user.id` on every session route | `app.py` chat, send_message, end_session, comparison |
| XSS (injecting scripts via chat) | `escapeHtml()` in JS + Jinja2 auto-escaping in templates | `chat.html` |
| SQL injection | SQLAlchemy parameterizes all queries — no raw SQL anywhere | everywhere |
| Cookie tampering | Session cookie signed with SECRET_KEY | `config.py` |
| Self-harm crisis mishandled by AI | Hardcoded keyword detection BEFORE the AI, fixed response with hotlines | `gemini_api.py` |
| API key leakage | Key lives only in `.env`, which is gitignored | `.env`, `.gitignore` |
| Form re-submission (double post-survey) | DB unique constraint + route check | `models.py`, `app.py` |
| Bad input (assessment values) | Range validation 1–5 server-side | `app.py` |

---

## Part 6: How the Frontend Is Put Together

- **`base.html`** is the skeleton: `<head>`, CSS link, navbar block, and
  `{% block content %}{% endblock %}`. Every other template starts with
  `{% extends "base.html" %}` and fills the block. Change base once → every
  page changes.
- **`styles.css`** holds shared styles (cards, buttons, flash colors, chat
  bubbles, the typing-indicator animation). Some pages also have inline
  `<style>` blocks for page-specific styling.
- **JavaScript lives inline** in the templates that need it:
  - `chat.html`: sendMessage(), typing indicator, session timer, Enter-to-send
  - `register.html`: password strength meter
  - `journal.html`: character counter, mood pill selector
  - `breathing.html`: technique data + breathing animation timer
- **Flash messages** render via a Jinja2 loop reading
  `get_flashed_messages(with_categories=true)`; the category (success / error /
  warning / info) becomes a CSS class that controls the color.

---

## Part 7: The Database File Itself

- SQLite = the whole database is **one file**: `instance/mindease.db`.
  No server to install, perfect for development. The FYP plan migrates to
  PostgreSQL for production — only the `DATABASE_URL` would change, zero code
  changes, because SQLAlchemy abstracts the database away.
- Deleting that file and running `python database.py` gives you a fresh,
  empty database with the 10 seed quotes.
- `database.py` vs `db.create_all()` in app.py: create_all() makes missing
  tables on every startup (safe — it never touches existing ones);
  database.py is the explicit reset/seed script.

---

## Part 8: Likely Viva Questions and Answers

**Q: Why Flask and not Django?**
A: Flask is lightweight and unopinionated — right-sized for a 14-route app.
Django bundles an admin panel, its own ORM, and conventions MindEase doesn't
need. Flask let me choose exactly the components in my stack (SQLAlchemy,
Flask-Login).

**Q: Why does the bot remember the conversation?**
A: It doesn't — Gemini is stateless. I store every message in the database
and re-send the last 10 messages as context with every API call. The
"memory" is engineered on my side.

**Q: What happens if the Gemini API is down?**
A: Three-model fallback chain first; if all fail, a safe hardcoded supportive
message is returned. The user message is already saved, the app never crashes.

**Q: Why is crisis detection not done by the AI?**
A: Reliability. An LLM response is probabilistic; for self-harm content I need
a deterministic, guaranteed response with real hotline numbers. The keyword
check runs before the API call and short-circuits it.

**Q: Why pre AND post assessment?**
A: That's the measurement instrument of the project. The research question is
whether an AI chat session reduces stress — pre/post comparison on the same
5 dimensions gives a quantified per-session effectiveness score, which
commercial apps (Wysa, Woebot) don't expose to users.

**Q: Explain the effectiveness formula.**
A: All five dimensions are converted into a unified distress score (lower =
better) by inverting the positive dimensions: distress = stress + anxiety +
(6−mood) + (6−sleep) + (6−energy). Improvement = (pre−post)/pre × 100.
Inverting is necessary because raw totals would let a mood improvement cancel
out a stress reduction.

**Q: How do you prevent a user reading someone else's chats?**
A: Every session-related route re-checks ownership server-side:
`chat_session.user_id == current_user.id`. The session id in the URL or
payload is never trusted.

**Q: What is flush() vs commit()?**
A: flush() sends the pending INSERT to the database so the new row gets its
auto-generated id, but inside the still-open transaction; commit() makes it
permanent. I flush to get the ChatSession id, use it for the PreSurvey
foreign key, then commit both together — so they save atomically.

---

## Part 9: One-Paragraph Summary (memorize this)

> MindEase is a three-tier Flask web application. The presentation layer is 13
> Jinja2 templates with AJAX-based chat; the application layer is 14 Flask
> routes plus a Gemini API integration module with stress-adaptive prompting,
> hardcoded crisis detection, and a three-model fallback chain; the data layer
> is 9 SQLAlchemy models over SQLite. A user completes a 5-dimension
> pre-assessment which creates a ChatSession, chats with the AI (each exchange
> persisted and the last 10 messages re-sent as context), then completes a
> post-assessment. Effectiveness is computed as the percentage reduction in a
> direction-aware distress score, displayed per-session and aggregated on the
> dashboard. Authentication uses Flask-Login with Werkzeug password hashing,
> and every data-access route enforces ownership checks server-side.
