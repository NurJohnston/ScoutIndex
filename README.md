This was just a personal project messing about with the Gemini API. ScoutIndex is a football chatbot
— the context is limited to whatever it's set up for, which in this case is football. It runs on the 
Gemini REST API, but also has fallback or hardcoded knowledge in case the API is down. I built a 
Flask interface so you can actually interact with it in a browser. No API key is exposed — you need 
to get your own and put it in a .env file that the Python script reads and executes.


To run it:

git clone https://github.com/NurJohnston/ScoutIndex.git

cd ScoutIndex

pip install -r requirements.txt

python App.py
