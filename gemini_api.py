# gemini_api.py
# Restructured Direct Integration for MindEase 

import urllib.request
import json
import os

class GeminiChatbot:
    def __init__(self, api_key=None):
        # One or more API keys. The daily free-tier quota is per Google Cloud
        # project, so a backup key created in a different project keeps the
        # chatbot alive when the primary key's daily quota is exhausted.
        # .env supports either GEMINI_API_KEY or comma-separated GEMINI_API_KEYS.
        raw = (api_key or os.getenv('GEMINI_API_KEYS')
               or os.getenv('GEMINI_API_KEY') or "")
        self.api_keys = [k.strip() for k in raw.split(',') if k.strip()]

        # Each model also has its own quota, so if one is rate-limited
        # (HTTP 429) the next one is tried automatically.
        self.models = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
        ]

    @property
    def api_key(self):
        # Kept for backward compatibility with code that reads .api_key
        return self.api_keys[0] if self.api_keys else ""

    def _model_url(self, model, key):
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

    def detect_crisis_keywords(self, user_message):
        crisis_keywords = [
            'suicide', 'suicidal', 'kill myself', 'end it all',
            'want to die', 'wanna die', 'should die', 'i die', 'to die',
            'want to disappear', 'self harm', 'self-harm', 'hurt myself',
            'harm myself', 'cut myself', 'end my life', 'take my life',
            'no reason to live', 'nothing to live for', 'rather be dead',
            'better off dead', 'better off without me', 'cant go on',
            "can't go on", 'give up on life', 'not worth living'
        ]
        # Normalize: lowercase and collapse punctuation so "should die!" matches
        message_lower = ' '.join(user_message.lower().split())
        return any(keyword in message_lower for keyword in crisis_keywords)

    def get_crisis_response(self):
        return (
            "I'm really concerned about what you're sharing with me. "
            "Please reach out for immediate support:\n\n"
            "Befrienders Malaysia: 03-7956-8145 (available 24/7)\n"
            "Emergency: 999\n"
            "MMU Counselling Centre: 03-8312-5798\n\n"
            "You are not alone, and help is available right now. Please reach out to them."
        )

    def generate_response(self, user_message, stress_level, conversation_history=None):
        if self.detect_crisis_keywords(user_message):
            return self.get_crisis_response()
        
        # Adaptive tone GUIDANCE based on the pre-assessment stress level.
        # This shapes HOW the assistant speaks - it must NOT make the assistant
        # assume what the user is feeling or put words in their mouth.
        if stress_level >= 4:
            tone = (
                "Their pre-session check-in suggested they may be under a lot of pressure, "
                "so lean towards a calm, gentle and reassuring tone. If they share a problem, "
                "help break it into small, manageable steps."
            )
        elif stress_level == 3:
            tone = (
                "Their pre-session check-in suggested moderate stress, so be supportive and, "
                "when they raise a concern, gently explore coping strategies with them."
            )
        else:
            tone = (
                "Their pre-session check-in suggested they are doing relatively okay, so keep a "
                "warm, positive and encouraging tone."
            )

        system_context = (
            "You are MindEase, an empathetic mental-health support companion for university "
            "students. You are supportive, not a therapist - never diagnose or give medical advice.\n"
            "IMPORTANT rules:\n"
            "- Respond naturally to what the user ACTUALLY says. If they just greet you (e.g. "
            "'hello'), greet them back warmly and invite them to share what's on their mind - do "
            "NOT assume they are upset or tell them how they feel.\n"
            "- Never put words in their mouth or state their emotions as fact. Ask open, gentle "
            "questions instead of assuming.\n"
            "- Keep replies warm and concise (2-3 sentences).\n"
            "- Use plain text only. Do not use emojis.\n"
            f"- Tone guidance (background only, do not mention it): {tone}\n\n"
        )

        # Recent conversation context for coherent multi-turn dialogue
        history_text = ""
        if conversation_history:
            for msg in conversation_history[-10:]:
                speaker = "User" if msg['sender'] == 'user' else "MindEase"
                history_text += f"{speaker}: {msg['message']}\n"

        full_prompt = f"{system_context}{history_text}User: {user_message}\nMindEase:"

        result = self._generate(full_prompt)
        return result or "I am right here listening to you. Tell me a bit more about what's on your mind."

    def _generate(self, prompt, max_tokens=1024):
        """
        Send a prompt to Gemini, trying each model and each API key in turn.
        Free-tier quotas are per model AND per project (key), so a 429 on one
        combination does not mean the others are exhausted. Returns the reply
        text, or None if every model/key combination failed.
        """
        for model in self.models:
            generation_config = {"temperature": 0.7, "maxOutputTokens": max_tokens}
            # 2.5 models spend invisible "thinking" tokens against the output
            # budget and can truncate mid-sentence; give the whole budget to text.
            if model.startswith("gemini-2.5"):
                generation_config["thinkingConfig"] = {"thinkingBudget": 0}

            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": generation_config
            }
            data_bytes = json.dumps(payload).encode('utf-8')

            for i, key in enumerate(self.api_keys):
                try:
                    req = urllib.request.Request(
                        self._model_url(model, key),
                        data=data_bytes,
                        headers={'Content-Type': 'application/json'}
                    )
                    with urllib.request.urlopen(req, timeout=15) as response:
                        response_data = json.loads(response.read().decode('utf-8'))

                    if 'candidates' in response_data and len(response_data['candidates']) > 0:
                        parts = response_data['candidates'][0]['content'].get('parts', [])
                        if parts and 'text' in parts[0]:
                            return parts[0]['text'].strip()
                except urllib.error.HTTPError as e:
                    print(f"[API LOG] {model} (key {i+1}): HTTP {e.code} - trying next", flush=True)
                    continue
                except Exception as e:
                    print(f"[API LOG] {model} (key {i+1}): {e}", flush=True)
                    continue
        return None

    def generate_insights(self, data_summary):
        """
        AI Wellness Insights: analyse the user's structured wellness data
        (assessment trends, journal moods, activity counts) and return
        personalised observations. Uses only metadata/trends - never the
        private content of chat conversations.
        """
        prompt = (
            "You are MindEase's wellness insights assistant. Analyse ONLY the "
            "user's wellness data below and write 3 to 4 short, warm, specific "
            "insights for the user about their stress patterns, possible "
            "triggers, what seems to be helping, and one gentle suggestion.\n"
            "Rules:\n"
            "- Base everything strictly on the data provided; do NOT invent numbers.\n"
            "- Address the user as 'you'. Keep each insight to 1-2 sentences.\n"
            "- Plain text only, no emojis. Begin each insight on its own line with '- '.\n"
            "- If there is very little data, gently say that more sessions and journal "
            "entries will reveal clearer patterns.\n\n"
            f"WELLNESS DATA:\n{data_summary}\n\nINSIGHTS:"
        )
        result = self._generate(prompt, max_tokens=600)
        return result or ("Insights couldn't be generated right now (the AI service "
                          "may be busy). Please try again in a moment.")

    def get_conversation_starter(self, stress_level):
        if stress_level >= 4:
            return (
                "Hi, I'm really glad you're here. It sounds like things have been quite tough lately - "
                "a stress level of " + str(stress_level) + " out of 5 tells me you're carrying a lot right now. "
                "I'm here to listen without judgment. Take a breath, and whenever you're ready, tell me what's been going on."
            )
        elif stress_level == 3:
            return (
                "Hey, welcome. I can see you're feeling moderately stressed today (level " + str(stress_level) + "/5). "
                "That's completely okay - life gets overwhelming sometimes. "
                "I'm here to chat and support you. What's been on your mind lately?"
            )
        else:
            return (
                "Hello, good to see you today. You're starting at a stress level of " + str(stress_level) + "/5, "
                "which sounds manageable. I'm here to help you maintain that positive momentum. "
                "What would you like to talk about or work on today?"
            )

def create_chatbot():
    return GeminiChatbot()