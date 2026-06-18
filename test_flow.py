# test_flow.py
# End-to-end flow test for MindEase using Flask test client
# Tests: register -> login -> dashboard -> pre-assessment -> chat ->
#        send message -> end session -> post-assessment -> comparison ->
#        history -> breathing -> journal -> logout

import sys
sys.stdout.reconfigure(encoding="utf-8")

from app import app, db
from models import User

EMAIL = "testflow@mmu.edu.my"
PASSWORD = "testpass123"

results = []

def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'} - {name}" + (f" ({detail})" if detail else ""))

with app.app_context():
    # Clean slate for the test user
    existing = User.query.filter_by(email=EMAIL).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()

client = app.test_client()

# 1. Index page loads
r = client.get("/")
check("Index page", r.status_code == 200)

# 2. Register
r = client.post("/register", data={
    "email": EMAIL, "password": PASSWORD, "confirmPassword": PASSWORD,
    "fullname": "Test Flow", "ageGroup": "18-24"
}, follow_redirects=True)
check("Register", r.status_code == 200 and b"Registration successful" in r.data)

# 3. Login
r = client.post("/login", data={"email": EMAIL, "password": PASSWORD}, follow_redirects=True)
check("Login", r.status_code == 200 and b"Welcome back" in r.data)

# 4. Dashboard
r = client.get("/dashboard")
check("Dashboard", r.status_code == 200)

# 5. Pre-assessment GET + POST
r = client.get("/pre-assessment")
check("Pre-assessment page", r.status_code == 200)
r = client.post("/pre-assessment", data={
    "stress": 4, "mood": 2, "sleep": 2, "energy": 2, "anxiety": 4
}, follow_redirects=False)
check("Pre-assessment submit", r.status_code == 302 and "/chat" in r.headers.get("Location", ""))

# 6. Chat page (generates starter message)
r = client.get("/chat")
check("Chat page", r.status_code == 200)

# Get session id from the page
import re
m = re.search(rb"const SESSION_ID = (\d+)", r.data)
session_id = int(m.group(1)) if m else None
check("Session ID embedded in chat page", session_id is not None, f"id={session_id}")

# 7. Send a message (AJAX) - bot may use fallback if API rate-limited
r = client.post("/api/send-message", json={"message": "I'm stressed about my exams", "session_id": session_id})
data = r.get_json()
check("Send message API", r.status_code == 200 and data.get("success") and len(data.get("bot_message", "")) > 0,
      f"bot said: {data.get('bot_message', '')[:60]}...")

# 8. Crisis detection (hardcoded, never goes to Gemini)
r = client.post("/api/send-message", json={"message": "I want to end it all", "session_id": session_id})
data = r.get_json()
check("Crisis detection", "Befrienders" in data.get("bot_message", ""))

# 9. End session
r = client.post(f"/end-session/{session_id}", follow_redirects=False)
check("End session", r.status_code == 302 and "post-assessment" in r.headers.get("Location", ""))

# 10. Post-assessment
r = client.post("/post-assessment", data={
    "stress": 2, "mood": 4, "sleep": 3, "energy": 3, "anxiety": 2
}, follow_redirects=False)
check("Post-assessment submit", r.status_code == 302 and f"/comparison/{session_id}" in r.headers.get("Location", ""))

# 11. Comparison page with effectiveness + conversation transcript (IT-03)
r = client.get(f"/comparison/{session_id}")
check("Comparison page", r.status_code == 200)
check("Transcript on comparison page", b"Conversation Transcript" in r.data)

# Verify effectiveness math: pre total = 4+2+2+2+4 = 14, post = 2+4+3+3+2 = 14
from models import calculate_effectiveness
with app.app_context():
    eff = calculate_effectiveness(session_id)
check("Effectiveness calculated", eff is not None,
      f"pre={eff['pre_total']} post={eff['post_total']} improvement={eff['overall_improvement']}% status={eff['effectiveness_status']}")

# 12. History
r = client.get("/history")
check("History page", r.status_code == 200)

# 13. Breathing page + completion API
r = client.get("/breathing")
check("Breathing page", r.status_code == 200)
r = client.post("/api/complete-breathing", json={"technique": "Box"})
check("Complete breathing API", r.status_code == 200 and r.get_json().get("success"))

# 14. Journal GET + POST
r = client.get("/journal")
check("Journal page", r.status_code == 200)
r = client.post("/journal", data={"title": "Test Entry", "content": "Feeling better after the session.", "mood": "Calm"}, follow_redirects=False)
check("Journal submit", r.status_code == 302)

# 14b. Journal entries list, edit, delete
r = client.get("/journal/entries")
check("Journal entries list", r.status_code == 200 and b"Test Entry" in r.data)

from models import JournalEntry
with app.app_context():
    user = User.query.filter_by(email=EMAIL).first()
    entry = JournalEntry.query.filter_by(user_id=user.id).first()
    entry_id = entry.id

r = client.get(f"/journal/edit/{entry_id}")
check("Journal edit page prefilled", r.status_code == 200 and b"Test Entry" in r.data and b"Update Entry" in r.data)

r = client.post(f"/journal/edit/{entry_id}", data={"title": "Edited Title", "content": "Updated content.", "mood": "Happy"}, follow_redirects=True)
check("Journal edit submit", r.status_code == 200 and b"Edited Title" in r.data)

r = client.post(f"/journal/delete/{entry_id}", follow_redirects=True)
with app.app_context():
    gone = JournalEntry.query.get(entry_id) is None
check("Journal delete", r.status_code == 200 and gone)

# 15. Logout
r = client.get("/logout", follow_redirects=True)
check("Logout", r.status_code == 200)

# 16. Protected route redirects when logged out
r = client.get("/dashboard", follow_redirects=False)
check("Auth protection after logout", r.status_code == 302)

# 17. 404 handler
r = client.get("/nonexistent-page")
check("404 handler", r.status_code == 404)

# 18. Admin module (FYP1 test cases UT-05, IT-04)
admin_client = app.test_client()
r = admin_client.get("/admin", follow_redirects=False)
check("Admin guard blocks anonymous", r.status_code == 302)

r = admin_client.post("/admin/login", data={"username": "admin", "password": "wrong"}, follow_redirects=True)
check("Admin wrong password rejected", b"Invalid admin credentials" in r.data)

r = admin_client.post("/admin/login", data={"username": "admin", "password": "AdminPass456"}, follow_redirects=True)
check("Admin login (UT-05)", b"System Overview" in r.data)

r = admin_client.post("/admin/quotes", data={"quote_text": "Testing quote", "author": "Test Author"}, follow_redirects=True)
check("Admin add quote (IT-04)", b"Quote added successfully" in r.data)

from models import DailyMotivation
with app.app_context():
    q = DailyMotivation.query.filter_by(author="Test Author").first()
    qid = q.id
r = admin_client.post(f"/admin/quotes/toggle/{qid}", follow_redirects=True)
with app.app_context():
    toggled = DailyMotivation.query.get(qid).is_active == False
check("Admin toggle quote", toggled)

r = admin_client.post(f"/admin/quotes/delete/{qid}", follow_redirects=True)
with app.app_context():
    deleted = DailyMotivation.query.get(qid) is None
check("Admin delete quote", deleted)

# 19. Admin user management
r = admin_client.get("/admin/users")
check("Admin users list", r.status_code == 200 and b"User Management" in r.data)

r = admin_client.post("/admin/users/add", data={"email": "byadmin@test.my", "name": "By Admin", "password": "byadmin123"}, follow_redirects=True)
check("Admin add user", b"created" in r.data and b"byadmin@test.my" in r.data)

with app.app_context():
    new_uid = User.query.filter_by(email="byadmin@test.my").first().id
r = admin_client.post(f"/admin/users/delete/{new_uid}", follow_redirects=True)
with app.app_context():
    user_gone = User.query.get(new_uid) is None
check("Admin delete user", user_gone)

# 20. Admin analytics page with charts
r = admin_client.get("/admin/analytics")
check("Admin analytics page", r.status_code == 200 and b"growthChart" in r.data and b"moodChart" in r.data)

# 21. Mood-adaptive quotes (re-login: client was logged out above)
client.post("/login", data={"email": EMAIL, "password": PASSWORD}, follow_redirects=True)
r = client.get("/dashboard")
check("Dashboard mood picker", b"How are you feeling right now" in r.data and b"mood-chip" in r.data)

r = client.get("/api/random-quote?emotion=Anxious")
d = r.get_json()
check("Mood-adaptive quote API (Anxious)", d.get("success") and d.get("emotion") == "Anxious")

r = client.get("/api/random-quote?emotion=Neutral")
check("Neutral mood returns a quote", r.get_json().get("success"))

print()
passed = sum(1 for _, ok, _ in results if ok)
print(f"=== {passed}/{len(results)} checks passed ===")
sys.exit(0 if passed == len(results) else 1)
