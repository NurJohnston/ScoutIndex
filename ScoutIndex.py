import urllib.request
import json
import time

API_KEY = None
try:
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('GEMINI_API_KEY='):
                API_KEY = line.strip().split('=')[1]
                print("Loaded")
                break
except FileNotFoundError:
    pass

if not API_KEY:
    API_KEY = input("Paste your Gemini API key: ")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={API_KEY}"

class ScoutIndex:
    """Football knowledge chatbot - knows about players, clubs, transfers, and stats"""

    def __init__(self, api_key):
        self.api_key = api_key
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={API_KEY}"
        self.conversation_history = []

        self.system_prompt = {
            "role": "user",
            "parts": [{"text": "ScoutIndex: football expert. Short answers only. 2-3 sentences max. No made-up facts."}]
        }

        self.conversation_history.append(self.system_prompt)

    def ask(self, question):
        """Send a question to Gemini and get a response"""

        self.conversation_history.append({
            "role": "user",
            "parts": [{"text": question}]
        })

        data = {
            "contents": self.conversation_history,
            "generationConfig": {
                "maxOutputTokens": 40,
                "temperature": 0.3,
                "topP": 0.8,
                "topK": 40
            }
        }
        json_data = json.dumps(data).encode('utf-8')
        request = urllib.request.Request(self.url, data=json_data, method='POST')
        request.add_header('Content-Type', 'application/json')

        try:
            with urllib.request.urlopen(request) as response:
                result = json.loads(response.read().decode())
                answer = result['candidates'][0]['content']['parts'][0]['text']

                self.conversation_history.append({
                    "role": "model",
                    "parts": [{"text": answer}]
                })

                if len(self.conversation_history) > 41:
                    self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-40:]

                return answer

        except Exception as e:
            return f"Error: {e}"


print("=" * 60)
print("⚽ SCOUTINDEX - Football Knowledge AI")
print("=" * 60)
print("\nI know about:")
print("  • Players (stats, squad numbers, histories)")
print("  • Clubs (trophies, formations, transfers)")
print("  • Competitions (results, winners, records)")
print("\nType 'quit' to exit\n")

bot = ScoutIndex(API_KEY)

while True:
    user_input = input("You: ")

    if user_input.lower() == 'quit':
        print("\n⚽ ScoutIndex: Thanks for chatting football! Goodbye!")
        break

    if not user_input.strip():
        continue

    print("⚽ ScoutIndex: ", end="", flush=True)
    response = bot.ask(user_input)
    print(response)
    print()