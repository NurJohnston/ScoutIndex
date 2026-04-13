from flask import Flask, render_template, request, jsonify
import urllib.request
import json
import os
import time
import re

app = Flask(__name__)

# Load API key from .env file
API_KEY = None
try:
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('GEMINI_API_KEY='):
                API_KEY = line.strip().split('=')[1]
                print("✓ Loaded API key from .env")
                break
except FileNotFoundError:
    pass

if not API_KEY:
    API_KEY = input("Paste your Gemini API key: ")

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={API_KEY}"

# ============================================
# FALLBACK KNOWLEDGE BASE (for when API fails)
# ============================================
FALLBACK_QA = {
    1: {
        "question": "Who is the all-time top scorer in football history?",
        "answer": "Cristiano Ronaldo holds the official record with over 870 career goals. Messi follows with over 800."
    },
    2: {
        "question": "Which club has won the most Champions League titles?",
        "answer": "Real Madrid has won 14 Champions League titles, more than any other club."
    },
    3: {
        "question": "Who won the 2022 FIFA World Cup?",
        "answer": "Argentina won the 2022 World Cup, defeating France 4-2 on penalties."
    },
    4: {
        "question": "What is the offside rule?",
        "answer": "A player is offside if they are nearer to the opponent's goal than the ball and second-last opponent when the ball is played."
    },
    5: {
        "question": "Who has won the most Ballon d'Or awards?",
        "answer": "Lionel Messi has won 8 Ballon d'Or awards. Ronaldo has won 5."
    }
}

# Keywords to match natural language to fallback questions
FALLBACK_KEYWORDS = {
    1: ['top scorer', 'all-time scorer', 'most goals', 'career goals', 'ronaldo goals', 'messi goals', 'goal record',
        'highest scorer', 'leading scorer', 'all time top scorer'],
    2: ['champions league titles', 'ucl titles', 'most champions league', 'real madrid champions', 'club with most ucl',
        'ucl wins', 'champions league wins', 'most ucl titles'],
    3: ['world cup winner', '2022 world cup', 'qatar world cup', 'argentina world cup', 'france world cup',
        'world cup 2022', 'who won the world cup', 'world cup champion'],
    4: ['offside', 'offside rule', 'what is offside', 'offside explained', 'offside law', 'offside in football'],
    5: ['ballon d\'or', 'ballon dor', 'most ballon d\'or', 'messi ballon d\'or', 'ronaldo ballon d\'or',
        'ballon d\'or winner', 'golden ball', 'ballon dor winner']
}


def match_fallback_question(user_input):
    """Match user input to a fallback question using keywords"""
    user_lower = user_input.lower()

    # Check keyword matches
    for q_num, keywords in FALLBACK_KEYWORDS.items():
        for keyword in keywords:
            if keyword in user_lower:
                return q_num

    # Check for direct number input (e.g., "3" or "question 3")
    number_match = re.search(r'\b([1-5])\b', user_lower)
    if number_match:
        return int(number_match.group(1))

    return None


def is_football_related_ai(question):
    """Use Gemini to check if question is football-related"""
    check_prompt = f"""You are a football detector. Answer ONLY with "YES" or "NO".
Is this question about football (soccer)? 

Question: "{question}"

Answer YES or NO only:"""

    data = {
        "contents": [{"parts": [{"text": check_prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 10,
            "temperature": 0
        }
    }

    json_data = json.dumps(data).encode('utf-8')
    request = urllib.request.Request(url, data=json_data, method='POST')
    request.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.loads(response.read().decode())
            answer = result['candidates'][0]['content']['parts'][0]['text'].strip().upper()
            return answer == "YES"
    except Exception:
        # If API fails for detection, assume it's football to avoid blocking
        return True


def get_fallback_response(user_input):
    """Handle fallback when API fails - supports natural language matching"""

    # Try to match user input to a question
    matched_num = match_fallback_question(user_input)

    if matched_num:
        qa = FALLBACK_QA[matched_num]
        return f"⚽ {qa['answer']}"

    # If no match, show menu
    return f"⚽ Please ask one of these:\n{get_fallback_menu()}"


def get_fallback_menu():
    """Return the menu of hardcoded questions"""
    menu = "\n"
    for num, qa in FALLBACK_QA.items():
        menu += f"  {num}. {qa['question']}\n"
    return menu


class ScoutIndex:
    def __init__(self):
        self.conversation_history = []
        self.system_prompt = {
            "role": "user",
            "parts": [{
                "text": """ScoutIndex: football expert. Answer football questions honestly. Keep answers between one and fifteen words."""}]
        }
        self.conversation_history.append(self.system_prompt)
        self.api_failed = False

    def ask(self, question):
        # If API previously failed, go straight to fallback
        if self.api_failed:
            return get_fallback_response(question)

        # FIRST: Use AI to check if question is football related
        try:
            is_football = is_football_related_ai(question)
            if not is_football:
                return "Please keep questions football related. ⚽"
        except Exception:
            # If detection fails, assume it's football (better to answer than block)
            pass

        # Now send to main conversation
        self.conversation_history.append({
            "role": "user",
            "parts": [{"text": question}]
        })

        data = {
            "contents": self.conversation_history,
            "generationConfig": {
                "maxOutputTokens": 80,
                "temperature": 0.5
            }
        }

        json_data = json.dumps(data).encode('utf-8')
        request = urllib.request.Request(url, data=json_data, method='POST')
        request.add_header('Content-Type', 'application/json')

        # Retry logic
        max_retries = 3
        wait_time = 3

        for attempt in range(max_retries):
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
                error_msg = str(e)
                if attempt < max_retries - 1 and ("429" in error_msg or "503" in error_msg):
                    print(f"⚠️ API error. Retry {attempt + 1}/{max_retries} in {wait_time}s...")
                    time.sleep(wait_time)
                    wait_time = wait_time * 2
                else:
                    print(f"❌ API failed permanently: {error_msg}")
                    self.api_failed = True
                    return get_fallback_response(question)

        self.api_failed = True
        return get_fallback_response(question)


# Create chatbot instance
bot = ScoutIndex()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message', '')

    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    response = bot.ask(user_message)
    return jsonify({'response': response})


if __name__ == '__main__':
    print("=" * 50)
    print("⚽ ScoutIndex Web Server Starting...")
    print("=" * 50)
    print("\n📍 Open your browser and go to: http://127.0.0.1:5000")
    print("📍 Press Ctrl+C to stop the server\n")
    app.run(debug=True, port=5000)