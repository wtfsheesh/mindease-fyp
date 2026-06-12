# gemini_api.py
# Restructured Direct Integration for MindEase 

import urllib.request
import json
import os

class GeminiChatbot:
    def __init__(self, api_key=None):
        # Cleans up and stores your exact API key string
        self.api_key = (api_key or os.getenv('GEMINI_API_KEY') or "").strip()

        # Each model has its own free-tier quota, so if one is rate-limited
        # (HTTP 429) the next one is tried automatically.
        self.models = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
        ]

    def _model_url(self, model):
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"

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
            "🆘 Befrienders Malaysia: 03-7956-8145 (24/7)\n"
            "🚨 Emergency: 999\n"
            "🏫 MMU Counseling Centre: 03-8312-5798\n\n"
            "You are not alone, and help is available right now. Please reach out to them."
        )

    def generate_response(self, user_message, stress_level, conversation_history=None):
        if self.detect_crisis_keywords(user_message):
            return self.get_crisis_response()
        
        # Adaptive tone instructions based on pre-assessment stress level
        if stress_level >= 4:
            tone = (
                "The user is highly stressed. Use a calm, reassuring tone. "
                "Offer grounding techniques and break problems into small, manageable steps. "
                "Validate their feelings before suggesting anything."
            )
        elif stress_level == 3:
            tone = (
                "The user is moderately stressed. Be supportive and solution-focused. "
                "Validate their feelings and gently explore coping strategies with them."
            )
        else:
            tone = (
                "The user has low stress. Be positive and encouraging. "
                "Help build resilience and reinforce their healthy habits."
            )

        system_context = (
            "You are MindEase, an empathetic mental health support chatbot for university students. "
            "You are a supportive companion, not a therapist - never diagnose or give medical advice. "
            f"{tone} "
            "Keep your response warm and concise (maximum 2-3 sentences). "
            f"The user's current stress level is {stress_level} out of 5.\n\n"
        )

        # Recent conversation context for coherent multi-turn dialogue
        history_text = ""
        if conversation_history:
            for msg in conversation_history[-10:]:
                speaker = "User" if msg['sender'] == 'user' else "MindEase"
                history_text += f"{speaker}: {msg['message']}\n"

        full_prompt = f"{system_context}{history_text}User: {user_message}\nMindEase:"

        # Try each model in order - free-tier quotas are per model, so a
        # 429 on one model does not mean the others are exhausted.
        for model in self.models:
            generation_config = {
                "temperature": 0.7,
                "maxOutputTokens": 1024
            }
            # 2.5 models spend invisible "thinking" tokens that count against
            # maxOutputTokens and can truncate the visible reply mid-sentence.
            # A zero thinking budget gives the whole budget to the answer.
            if model.startswith("gemini-2.5"):
                generation_config["thinkingConfig"] = {"thinkingBudget": 0}

            payload = {
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generationConfig": generation_config
            }
            data_bytes = json.dumps(payload).encode('utf-8')

            try:
                req = urllib.request.Request(
                    self._model_url(model),
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
                print(f"\n[API LOG] {model}: HTTP {e.code} - trying next model\n")
                continue
            except Exception as e:
                print(f"\n[API LOG] {model}: {e}\n")
                continue

        return "I am right here listening to you. Tell me a bit more about what's on your mind."

    def get_conversation_starter(self, stress_level):
        if stress_level >= 4:
            return (
                "Hi, I'm really glad you're here. 💙 It sounds like things have been quite tough lately — "
                "a stress level of " + str(stress_level) + " out of 5 tells me you're carrying a lot right now. "
                "I'm here to listen without judgment. Take a breath, and whenever you're ready, tell me what's been going on."
            )
        elif stress_level == 3:
            return (
                "Hey, welcome! 😊 I can see you're feeling moderately stressed today (level " + str(stress_level) + "/5). "
                "That's completely okay — life gets overwhelming sometimes. "
                "I'm here to chat and support you. What's been on your mind lately?"
            )
        else:
            return (
                "Hello! Great to see you today. 🌟 You're starting at a stress level of " + str(stress_level) + "/5, "
                "which sounds manageable. I'm here to help you maintain that positive momentum. "
                "What would you like to talk about or work on today?"
            )

def create_chatbot():
    return GeminiChatbot()