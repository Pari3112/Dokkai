from flask import Flask, redirect, url_for, render_template, request, session, send_file,  request, session, flash
import pandas as pd
from gtts import gTTS
import os
import random
import numpy as np
from flask import make_response  # Import for creating responses
import sqlite3
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Generate a 24-byte secret key

# SQLite Database setup
DATABASE = 'users.db'

# Function to create the database if it doesn't exist
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')

        # Create answers table with the required schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                word TEXT,
                response TEXT,
                correct BOOLEAN,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create table to store user answers
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reading (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                word TEXT,
                selected_image TEXT,
                correct BOOLEAN,
                level TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS writting (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                question TEXT NOT NULL,
                user_response TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                correct BOOLEAN NOT NULL
            )
        """)
        conn.commit()
        

init_db()  # Initialize database with updated schema


# --------------------------------- User Authentication Routes --------------------------------- #

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if not name or not email or not password:
            flash("All fields are required!", "error")
            return redirect(url_for('signup'))

        # Save user to the database
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
                conn.commit()
                flash("Signup successful! Please login.", "success")
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash("Email already registered.", "error")
                return redirect(url_for('signup'))

    return render_template('signup.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Check user credentials
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
            user = cursor.fetchone()

            if user:
                session['user_id'] = user[0]  # Store user ID in the session
                session['user_name'] = user[1]  # Store user name in the session
                flash("Login successful!", "success")
                return redirect(url_for('home'))
            else:
                flash("Invalid email or password.", "error")
                return redirect(url_for('login'))

    return render_template('login.html')



@app.route('/logout')
def logout():
    session.clear()  # Clear the session
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))


# --------------------------------- Existing Routes --------------------------------- #



@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Pass the logged-in user's name to the home page
    user_name = session.get('user_name', 'User')
    return render_template('index.html', user_name=user_name)


def get_user_details(user_id):
    """Fetch user details from the database."""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, email FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        if result:
            return {"name" : result[0], "email": result[1]}
        return None



@app.route("/")
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    return render_template("index.html", user_name=session.get('user_name'))



# --------------------------------- ## --------------------------------- ## --------------------------------- #
################################ LISTENING #########################################

from flask import Flask, jsonify, render_template, request, session, redirect, url_for, flash, send_file

# Directory for audio files
audio_dir = "audio"
os.makedirs(audio_dir, exist_ok=True)

import openai

openai.api_key = os.getenv("API_KEY")

# List of tricky words and difficulty levels
tricky_words = [
    "knight", "wrist", "doubt", "honest", "island", "psychology", "gnome", "debt", "subtle",
    "knife", "plumber", "drought", "castle", "often", "listen", "receipt", "muscle", "sword",
    "mnemonic", "hour", "calf", "answer", "ghost", "knock", "whistle", "thumb", "fasten",
    "autumn", "psychiatrist", "gnaw", "comb", "design", "foreign", "half", "salmon", "debris",
    "yacht", "ballet", "chorus", "echo", "chaos", "aisle", "heir", "tomb", "honor", "scissors",
    "deceive", "hymn", "almond", "sword", "condemn", "rhyme"
]

difficulty_levels = {
    "easy": ["honest", "island", "hour", "calf", "listen", "ghost", "knife", "plumber", "often", "thumb"],
    "medium": ["doubt", "gnome", "debt", "receipt", "muscle", "autumn", "knock", "whistle", "fasten", "answer"],
    "hard": ["knight", "wrist", "psychology", "subtle", "mnemonic", "psychiatrist", "gnaw", "salmon", "debris", "yacht"]
}


import re
def sanitize_filename(filename):
    # Replace invalid characters with underscores
    return re.sub(r'[^\w.-]', '_', filename)

def generate_audio(word):
    sanitized_word = sanitize_filename(word)
    file_path = os.path.join(audio_dir, f"{sanitized_word}.mp3")
    if not os.path.exists(file_path):
        tts = gTTS(word, lang="en")
        tts.save(file_path)
    return file_path


# def generate_audio(word):
#     file_path = os.path.join(audio_dir, f"{word}.mp3")
#     if not os.path.exists(file_path):
#         tts = gTTS(word, lang="en")
#         tts.save(file_path)
#     return file_path

for word in tricky_words:
    generate_audio(word)

def get_question(level):
    word = random.choice(difficulty_levels[level])
    return {"word": word, "audio": f"/audio/{word}"}

@app.route('/audio/<word>')
def serve_audio(word):
    file_path = os.path.join(audio_dir, f"{word}.mp3")
    if os.path.exists(file_path):
        return send_file(file_path, mimetype="audio/mpeg")
    return jsonify({"error": "Audio file not found"}), 404

@app.route('/start_listen')
def start_listen():
    session['answers'] = []  # Initialize answers list
    session['attempts'] = 0  # Track the number of words listened to
    return redirect(url_for('listen'))

def save_answers_to_db(user_id, answers):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        for answer in answers:
            cursor.execute(
                "INSERT INTO answers (user_id, word, response, correct) VALUES (?, ?, ?, ?)",
                (user_id, answer["word"], answer["response"], answer["correct"])
            )
        conn.commit()

@app.route('/listen', methods=['GET', 'POST'])
def listen():
    if 'user_id' not in session:
        flash("You must log in to access this feature.", "error")
        return redirect(url_for('login'))

    if 'answers' not in session:
        session['answers'] = []
    if 'attempts' not in session:
        session['attempts'] = 0

    if request.method == 'GET':
        if session['attempts'] >= 10:
            save_answers_to_db(session['user_id'], session['answers'])  # Save results
            flash("Thanks for playing! Your results have been saved.", "info")
            return render_template("completion.html")  # Show completion message

        level = "easy"  # Default level for new sessions
        question = get_question(level)
        return render_template(
            "listening.html",
            word=question["word"],
            audio=question["audio"],
            level=level,
            correct=None
        )

    word = request.form.get("word")
    response = request.form.get("response")
    level = request.form.get("level")

    if not word or not response or not level:
        return render_template("error.html", message="Invalid input! Please try again.")

    correct = (word.lower() == response.lower())

    session['answers'].append({
        "word": word,
        "response": response,
        "correct": correct
    })

    session['attempts'] += 1

    if session['attempts'] >= 10:
        save_answers_to_db(session['user_id'], session['answers'])  # Save results
        flash("Thanks for playing! Your results have been saved.", "info")
        return render_template("completion.html")  # Show completion message

    next_level = "medium" if level == "easy" else "hard" if level == "medium" else "hard"
    if not correct:
        next_level = "easy" if level == "medium" else "medium" if level == "hard" else "easy"

    question = get_openai_question(level=next_level, previous_word=word, correct=correct)
    generate_audio(question['word'])  # Generate audio for the new word if not already done
    return render_template(
        "listening.html",
        word=question["word"],
        audio=question["audio"],
        level=next_level,
        correct=correct
    )
def get_openai_question(level, previous_word, correct):
    prompt = (
        f"Suggest a {level} level word similar to '{previous_word}' for a spelling listening game. "
        f"The previous answer was {'correct' if correct else 'incorrect'}."
    )
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Or gpt-4-turbo if available
        messages=[
            {"role": "system", "content": " Generate a single  word that people with dyslexia would find challenging. Ensure it is a single word only and avoid adding any explanations or additional context and give it in lowercase."},
            {"role": "user", "content": prompt}
        ]
    )
    # Extract the word and sanitize it
    word = response['choices'][0]['message']['content'].strip()
    word = sanitize_filename(word.split()[0])  # Take only the first word if there’s extra context
    return {"word": word, "audio": f"/audio/{word}"}

# # Generate Audio for All Words
# audio_dir = "audio"
# os.makedirs(audio_dir, exist_ok=True)

# tricky_words = [
#     "knight", "wrist", "doubt", "honest", "island", "psychology", "gnome", "debt", "subtle",
#     "knife", "plumber", "drought", "castle", "often", "listen", "receipt", "muscle", "sword", 
#     "mnemonic", "hour", "calf", "answer", "ghost", "knock", "whistle", "thumb", "fasten",
#     "autumn", "psychiatrist", "gnaw", "comb", "design", "foreign", "half", "salmon", "debris", 
#     "yacht", "ballet", "chorus", "echo", "chaos", "aisle", "heir", "tomb", "honor", "scissors", 
#     "deceive", "hymn", "almond", "sword", "condemn", "rhyme"
# ]

# difficulty_levels = {
#     "easy": ["honest", "island", "hour", "calf", "listen", "ghost", "knife", "plumber", "often", "thumb"],
#     "medium": ["doubt", "gnome", "debt", "receipt", "muscle", "autumn", "knock", "whistle", "fasten", "answer"],
#     "hard": ["knight", "wrist", "psychology", "subtle", "mnemonic", "psychiatrist", "gnaw", "salmon", "debris", "yacht"]
# }

# def generate_audio(word):
#     file_path = os.path.join(audio_dir, f"{word}.mp3")
#     if not os.path.exists(file_path):
#         tts = gTTS(word, lang="en")
#         tts.save(file_path)
#     return file_path

# for word in tricky_words:
#     generate_audio(word)

# # Listening Game Routes
# def get_question(level):
#     word = random.choice(difficulty_levels[level])
#     return {"word": word, "audio": f"/audio/{word}"}

# @app.route('/audio/<word>')
# def serve_audio(word):
#     file_path = os.path.join(audio_dir, f"{word}.mp3")
#     if os.path.exists(file_path):
#         return send_file(file_path, mimetype="audio/mpeg")
#     return jsonify({"error": "Audio file not found"}), 404


# @app.route('/start_listen')
# def start_listen():
#     # Properly initialize session keys
#     session['answers'] = []  # Initialize answers list
#     session['attempts'] = 0  # Track the number of words listened to
#     return redirect(url_for('listen'))



# def save_answers_to_db(user_id, answers):
#     with sqlite3.connect(DATABASE) as conn:
#         cursor = conn.cursor()
#         for answer in answers:
#             cursor.execute(
#                 "INSERT INTO answers (user_id, word, response, correct) VALUES (?, ?, ?, ?)",
#                 (user_id, answer["word"], answer["response"], answer["correct"])
#             )
#         conn.commit()

# @app.route('/listen', methods=['GET', 'POST'])
# def listen():
#     # Ensure the user is logged in
#     if 'user_id' not in session:
#         flash("You must log in to access this feature.", "error")
#         return redirect(url_for('login'))

#     # Initialize session variables for answers and attempts
#     if 'answers' not in session:
#         session['answers'] = []
#     if 'attempts' not in session:
#         session['attempts'] = 0

#     if request.method == 'GET':
#         # Check if user has completed 10 words
#         if session['attempts'] >= 2:
#             save_answers_to_db(session['user_id'], session['answers'])  # Save results
#             flash("Thanks for playing! Your results have been saved.", "info")
#             return render_template("completion.html")  # Show completion message

#         # Generate a new question
#         level = "easy"  # Default level for new sessions
#         question = get_question(level)
#         return render_template(
#             "listening.html",
#             word=question["word"],
#             audio=question["audio"],
#             level=level,
#             correct=None
#         )

#     # Process POST request (user submits their response)
#     word = request.form.get("word")
#     response = request.form.get("response")
#     level = request.form.get("level")

#     # Validate input
#     if not word or not response or not level:
#         return render_template("error.html", message="Invalid input! Please try again.")

#     # Determine correctness of the answer
#     correct = (word.lower() == response.lower())

#     # Append the result to session['answers']
#     session['answers'].append({
#         "word": word,
#         "response": response,
#         "correct": correct
#     })

#     # Increment the attempts count
#     session['attempts'] += 1

#     # Check if the user has completed 10 words
#     if session['attempts'] >= 10:
#         save_answers_to_db(session['user_id'], session['answers'])  # Save results
#         flash("Thanks for playing! Your results have been saved.", "info")
#         return render_template("completion.html")  # Show completion message

#     # Adjust difficulty level for the next question
#     next_level = "medium" if level == "easy" else "hard" if level == "medium" else "hard"
#     if not correct:
#         next_level = "easy" if level == "medium" else "medium" if level == "hard" else "easy"

#     # Generate the next question
#     question = get_question(next_level)
#     return render_template(
#         "listening.html",
#         word=question["word"],
#         audio=question["audio"],
#         level=next_level,
#         correct=correct
#     )


# --------------------------------- ## --------------------------------- ## --------------------------------- #

################################ READING #########################################

# Homophones data with images
homophones = {
    'Easy': [
    {'word': 'bin', 'images': [('bin.png', 'correct'), ('fin.png', 'incorrect'), ('win.png', 'incorrect')]},
    {'word': 'mat', 'images': [('mat.png', 'correct'),('hat.png', 'incorrect'), ('bat.png', 'incorrect')]},
    {'word': 'pan', 'images': [('pan.png', 'correct'), ('fan.png', 'incorrect'), ('man.png', 'incorrect'),]},
    {'word': 'pen', 'images': [('pen.png', 'correct'), ('ten.png', 'incorrect'), ('when.png', 'incorrect')]},
],
'Medium': [
    {'word': 'clue', 'images': [('clue.png', 'correct'), ('blue.png', 'incorrect'), ('cube.png', 'incorrect')]},
    {'word': 'jump', 'images': [('jump.png', 'correct'), ('camp.png', 'incorrect'), ('stamp.png', 'incorrect')]},
],
'Hard': [
    {'word': 'bird', 'images': [('bird.png', 'correct'), ('bride.png', 'incorrect'), ('bridge.png', 'incorrect')]},
    {'word': 'couch', 'images': [('couch.png', 'correct'), ('much.png', 'incorrect'), ('ouch.png', 'incorrect')]},
]

}


def init_session():
    session['Reading_level'] = 'Easy'
    session['correct_streak'] = 0
    session['answered_questions'] = 0
    session['current_question'] = None


# Get a random question based on difficulty
def get_question_reading(level):
    return random.choice(homophones[level])
    # question_data = random.choice(homophones[level])
    # session['current_question'] = question_data
    # return question_data

@app.route('/play_game', methods=['GET', 'POST'])
def play_game():
    if 'Reading_level' not in session:
        init_session()

    if session['answered_questions'] >= 10:
        flash("Thank you! You can view your score in the dashboard.", "success")
        return redirect(url_for('home'))

    if request.method == 'POST':
        answer = request.form.get('answer')  # 'correct' or 'incorrect'
        selected_image = (
            session['current_question']['images'][0][0]
            if answer == 'correct'
            else 'incorrect'
        )
        word = session['current_question']['word']
        correct = answer == 'correct'

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO reading (user_id, word, selected_image, correct, level)
                VALUES (?, ?, ?, ?, ?)
            ''', (session['user_id'], word, selected_image, correct, session['Reading_level']))
            conn.commit()

        if correct:
            session['correct_streak'] += 1
            if session['correct_streak'] >= 2:
                session['Reading_level'] = 'Medium' if session['Reading_level'] == 'Easy' else 'Hard'
        else:
            session['correct_streak'] = 0

        session['answered_questions'] += 1
        return redirect(url_for('play_game'))

    question = get_question_reading(session['Reading_level'])
    session['current_question'] = question
    return render_template('reading.html', level=session['Reading_level'], word=question['word'], images=question['images'])


@app.route('/restart')
def restart():
    init_session()
    return redirect(url_for('play_game'))




# --------------------------------- ## --------------------------------- ## --------------------------------- #

################################ WRITING #########################################


import pandas as pd
from gtts import gTTS
import os
import random

# Writing Questions Data
WRITING_QUESTIONS = {
    "easy": [
        {"type": "image", "image": "static/img/ball.png", "word": "ball"},
        {"type": "image", "image": "static/img/hat.png", "word": "hat"},
        {"type": "image", "image": "static/img/wall.png", "word": "wall"},
        {"type": "image", "image": "static/img/cup.png", "word": "cup"},
        {"type": "image", "image": "static/img/bell.png", "word": "bell"},
        {"type": "image", "image": "static/img/bear.png", "word": "bear"},
        
    ],
    "medium": [
        {"type": "image", "image": "static/img/hair.png", "word": "hair"},
        {"type": "image", "image": "static/img/chair.png", "word": "chair"},
        {"type": "image", "image": "static/img/chain.png", "word": "chain"},
        {"type": "image", "image": "static/img/deer.png", "word": "deer"},
        
        
    ],
    "hard": [
        {"type": "image", "image": "static/img/broccoli.png", "word": "broccoli"},
        {"type": "image", "image": "static/img/desert.png", "word": "desert"},
        {"type": "image", "image": "static/img/dessert.png", "word": "dessert"},
        {"type": "image", "image": "static/img/calendar.png", "word": "calendar"},
        {"type": "image", "image": "static/img/chameleon.png", "word": "chameleon"},
    ]

}

# Helper function to save result
def save_result(user_id, question, user_response, correct_answer, is_correct):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO writting (user_id, question, user_response, correct_answer, correct)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, question, user_response, correct_answer, is_correct))
        conn.commit()


# Route for "Writing" Game
@app.route("/writing", methods=["GET", "POST"])
def writing():
    if "current_question_index" not in session:
        session["current_question_index"] = 0
        session["score"] = 0
        session["level"] = "easy"
        session["questions"] = random.sample(WRITING_QUESTIONS["easy"], 2) + \
                               random.sample(WRITING_QUESTIONS["medium"], 2) + \
                               random.sample(WRITING_QUESTIONS["hard"], 2)

    current_index = session["current_question_index"]
    questions = session["questions"]

    if current_index >= 10:  # End game after 10 questions
        final_score = session.pop("score", 0)
        session.pop("current_question_index", None)
        session.pop("questions", None)
        return render_template("writing_result.html", score=final_score)

    current_question = questions[current_index]

    if request.method == "POST":
        user_input = request.form.get("answer", "").strip().lower()
        correct_answer = current_question["word"].lower()

        is_correct = user_input == correct_answer
        if is_correct:
            session["score"] += 1
        else:
            # If wrong, repeat the question or give a similar one
            questions.append(current_question)

        save_result(session.get("user_id", "guest"), str(current_question), user_input, correct_answer, is_correct)
        session["current_question_index"] += 1
        return redirect(url_for("writing"))

    return render_template(
        "writing_question.html",
        question=current_question,
        current_index=current_index + 1,
        total=10,
    )

# Writing Result Page
@app.route("/writing_result")
def writing_result():
    return "<h1>Thank you, You can view the score in your dashboard!</h1>"
  

# --------------------------------- ## --------------------------------- ## --------------------------------- #
################################ miscellaneous #########################################


# @app.route('/miscellaneous')
# def miscellaneous():
#     return render_template('miscellaneous.html')

# Question data for Miscellaneous challenges
quiz_questions = [
    # Existing Questions
    {
        "id": 1,
        "type": "time",
        "question": "Which clock shows 2:30?",
        "options": [
            {"id": 1, "image": "345.png"},
            {"id": 2, "image": "320.png"},
            {"id": 3, "image": "230.png"}
        ],
        "answer": 3
    },
    {
        "id": 2,
        "type": "direction",
        "question": "Which sign indicates a LEFT turn?",
        "options": [
            {"id": 1, "image": "right.png"},
            {"id": 2, "image": "left.png"}
        ],
        "answer": 2
    },
    
    {
        "id": 3,
        "type": "direction",
        "question": "Which sign indicates a left U-turn?",
        "options": [
            {"id": 1, "image": "uright.png"},
            {"id": 2, "image": "uleft.png"}
        ],
        "answer": 2
    },
    {
        "id": 4,
        "type": "pattern",
        "question": "Which sign indicates a left turn?",
        "options": [
            {"id": 1, "image": "loop.png"},
            {"id": 2, "image": "left.png"},
            
        ],
        "answer": 2
    },
    {
        "id": 5,
        "type": "color",
        "question": "Which clock shows 4:15?",
        "options": [
            {"id": 1, "image": "515.png"},
            {"id": 2, "image": "415.png"},
            
        ],
        "answer": 2
    },
    {
        "id": 6,
        "type": "direction",
        "question": "Which sign shows the NORTH direction?",
        "options": [
            {"id": 1, "image": "south.png"},
            {"id": 2, "image": "north.png"},
        
        ],
        "answer": 2
    },
    
]


@app.route('/miscellaneous', methods=['GET', 'POST'])
def miscellaneous():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Initialize quiz progress
    if 'quiz_index' not in session:
        session['quiz_index'] = 0
        session['score'] = 0

    if request.method == 'POST':
        # Check the previous answer
        selected_option = int(request.form.get('option', 0))
        correct_answer = quiz_questions[session['quiz_index']]['answer']

        if selected_option == correct_answer:
            session['score'] += 1

        session['quiz_index'] += 1

        # If quiz is complete, redirect to results
        if session['quiz_index'] >= len(quiz_questions):
            return redirect(url_for('quiz_result'))

    current_question = quiz_questions[session['quiz_index']]
    return render_template('quiz.html', question=current_question)

@app.route('/quiz_result')
def quiz_result():
    score = session.get('score', 0)
    total_questions = len(quiz_questions)

    # Clear session quiz progress
    session.pop('quiz_index', None)
    session.pop('score', None)

    return render_template('result.html', score=score, total=total_questions)





# --------------------------------- ## --------------------------------- ## --------------------------------- #
################################ Dashborad #########################################

@app.route('/dashboard') 
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Fetch user details
    user_details = get_user_details(session['user_id'])
    if not user_details:
        return "User not found.", 404

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()

        # Fetch listening game results and calculate percentage
        cursor.execute("""
            SELECT word, response, correct, timestamp
            FROM answers
            WHERE user_id = ?
        """, (session['user_id'],))
        user_answers = cursor.fetchall()
        total_listening = len(user_answers)
        correct_listening = sum(1 for _, _, correct, _ in user_answers if correct)
        listening_percentage = (correct_listening / total_listening) * 100 if total_listening else 0


        # Fetch reading game results and calculate percentage
        cursor.execute("""
            SELECT word, selected_image, correct, timestamp
            FROM reading
            WHERE user_id = ?
        """, (session['user_id'],))
        reading_results = cursor.fetchall()
        total_reading = len(reading_results)
        correct_reading = sum(1 for _, _, correct, _ in reading_results if correct)
        reading_percentage = (correct_reading / total_reading) * 100 if total_reading else 0



        # Fetch writing game results and calculate percentage
        cursor.execute("""
            SELECT question, user_response, correct_answer, correct
            FROM writting
            WHERE user_id = ?
        """, (session['user_id'],))
        writing_results = cursor.fetchall()
        total_writing = len(writing_results)
        correct_writing = sum(1 for _, _, _, correct in writing_results if correct)
        writing_percentage = (correct_writing / total_writing) * 100 if total_writing else 0


        # Calculate overall percentage (if needed)
        total_answers = total_listening + total_reading + total_writing
        total_correct = correct_listening + correct_reading + correct_writing
        overall_percentage = (total_correct / total_answers) * 100 if total_answers else 0


    return render_template(
        'dashboard.html', 
        user_details=user_details, 
        user_answers=user_answers, 
        reading_results=reading_results,
        writing_results=writing_results,
        listening_percentage=listening_percentage,
        reading_percentage=reading_percentage,
        writing_percentage=writing_percentage,
        overall_percentage=overall_percentage # Include if you want overall
    )
    
# --------------------------------- ## --------------------------------- ## --------------------------------- #


if __name__ == "__main__":
	app.run(debug=True)
