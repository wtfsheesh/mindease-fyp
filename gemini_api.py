# gemini_api.py
# Restructured Direct Integration for MindEase 

import urllib.request
import json
import os

class GeminiChatbot:
    def __init__(self, api_key=None):
        # Cleans up and stores your exact API key string
        self.api_key = (api_key or os.getenv('GEMINI_API_KEY') or "").strip()
        
        # gemini-2.0-flash is the current free-tier model (1.5-flash is deprecated)
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"

    def detect_crisis_keywords(self, user_message):
        crisis_keywords = [
            'suicide', 'kill myself', 'end it all', 'want to die',
            'self harm', 'hurt myself', 'end my life', 'no reason to live',
            'rather be dead', 'better off dead', 'cant go on'
        ]
        message_lower = user_message.lower()
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
        
        try:
            # Structuring the instructions as the profile baseline
            system_context = (
                "You are MindEase, an empathetic mental health support chatbot for university students. "
                f"Keep your response warm, deeply supportive, and concise (maximum 2-3 sentences). "
                f"The user's currently measured stress level is {stress_level} out of 5.\n\n"
            )
            
            # Appending recent conversation context history safely
            history_text = ""
            if conversation_history:
                for msg in conversation_history[-4:]:
                    speaker = "User" if msg['sender'] == 'user' else "MindEase"
                    history_text += f"{speaker}: {msg['message']}\n"
            
            # Merging everything into a single structured text container
            full_prompt = f"{system_context}{history_text}User: {user_message}\nMindEase:"
            
            # Exact JSON structure required by the Gemini API architecture
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": full_prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 150
                }
            }
            
            # Encoding payload to binary format for the web socket transmission
            data_bytes = json.dumps(payload).encode('utf-8')
            
            req = urllib.request.Request(
                self.url, 
                data=data_bytes, 
                headers={'Content-Type': 'application/json'}
            )
            
            # Executing standard web request
            with urllib.request.urlopen(req, timeout=10) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                
                # Reading text candidate values out of the response payload
                if 'candidates' in response_data and len(response_data['candidates']) > 0:
                    parts = response_data['candidates'][0]['content']['parts']
                    if len(parts) > 0 and 'text' in parts[0]:
                        return parts[0]['text'].strip()
            
            return "I hear you completely. Can you tell me a little bit more about what's going on?"
                    
        except Exception as e:
            print(f"\n[API CONNECTION LOG]: {e}\n")
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