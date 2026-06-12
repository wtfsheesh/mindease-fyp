# gemini_api.py
# Restructured Direct Integration for MindEase 

import urllib.request
import json
import os

class GeminiChatbot:
    def __init__(self, api_key=None):
        # Cleans up and stores your exact API key string
        self.api_key = (api_key or os.getenv('GEMINI_API_KEY') or "REDACTED").strip()
        
        # Using the standard v1 Beta endpoint which has the widest model accessibility layout
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"

    def detect_crisis_keywords(self, user_message):
        crisis_keywords = ['suicide', 'kill myself', 'end it all', 'want to die', 'self harm', 'hurt myself']
        message_lower = user_message.lower()
        return any(keyword in message_lower for keyword in crisis_keywords)
    
    def get_crisis_response(self):
        return "I'm concerned about what you're sharing. Please reach out to Befrienders Malaysia: 03-7956-8145 for immediate support."

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
        return f"Hi there! I see you're at a stress level of {stress_level} out of 5. I'm here to listen and support you. What's on your mind today?"

def create_chatbot():
    return GeminiChatbot()