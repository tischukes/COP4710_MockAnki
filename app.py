from flask import Flask, jsonify, request, render_template, redirect, url_for, session, flash 
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime
from datetime import timedelta as td
import os
import pymysql
import random
from simple_spaced_repetition import Card
from wiki_api import fetch_wikipedia_article, remove_references, process_text, translate_words

load_dotenv()

app = Flask(__name__)
app.secret_key = 'capybara'

# Get MySQL connection details from environment variables
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DB = os.getenv('MYSQL_DB')

class NewCard(Card):
    def __init__(self, id, front, back, last_reviewed=None, interval=None, ease=2.5, step=0, status='learning'):
        
        interval_td = td(seconds=interval) if isinstance(interval, (int, float)) else interval
        super().__init__(status=status, interval=interval_td, ease=ease, step=step)

        self.id = id
        self.front = front
        self.back = back

        if isinstance(last_reviewed, str):
            self.last_reviewed = datetime.strptime(last_reviewed, "%Y-%m-%d %H:%M:%S")
        elif isinstance(last_reviewed, float):
            self.last_reviewed = datetime.fromtimestamp(last_reviewed)
        else:
            self.last_reviewed = last_reviewed or datetime.now()
    def grade_answer(self, response):
        option_dict = dict(self.options())
        if response not in option_dict:
            raise ValueError(f"Invalid response: {response}")
        
        next_state = option_dict[response]

        self.status = next_state.status
        self.interval = next_state.interval
        self.ease = next_state.ease
        self.step = next_state.step
        self.last_reviewed = datetime.now()
    
def get_db_connection():
    connection = pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        db=MYSQL_DB,  # the database you want to use
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection

shuffled_cards = []
current_card_index = 0 

@app.route('/')
def index():
    if 'user_id' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor: # aggregate function 
            cursor.execute("""
                SELECT decks.id, decks.name, COUNT(flashcards.id) AS flashcard_count
                FROM decks
                LEFT JOIN flashcards ON flashcards.deck_id = decks.id
                GROUP BY decks.id
                ORDER BY decks.name
            """)
            decks = cursor.fetchall()
        connection.close()
        return render_template('index.html', decks=decks)
    else: 
        return render_template('signinpage.html')

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_pw = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)", 
                       (username, email, hashed_pw))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    print("Request method:", request.method)

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            print("Login successful.")
            return redirect(url_for('index'))
        else:
            print("Invalid credentials.")

    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)  # Remove the user_id from the session
    return redirect(url_for('signinpage'))

@app.route('/signinpage')
def signinpage():
    return render_template('signinpage.html')

@app.route('/deck/<int:deck_id>', methods=['GET'])
def print_deck(deck_id):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM decks WHERE id = %s",(deck_id,))
        deck=cursor.fetchone()

        if deck is None: 
            return "Deck not found!", 404
        
        deck_name = deck['name']
        cursor.execute("SELECT * FROM flashcards WHERE deck_id = %s", (deck_id,))
        flashcards = cursor.fetchall()
    connection.close()
    
    if deck:
        return render_template('deck.html', deck_name=deck_name, flashcards=flashcards, deck_id=deck_id)


@app.route('/add_deck', methods=['POST'])
def add_deck():
    deck_name = request.form['deck_name']

    if deck_name:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("INSERT INTO decks (name) VALUES (%s)", (deck_name,))
        connection.commit()

        connection.close()

        return redirect(url_for('index'))
    else:
        return jsonify({"message": "Deck name cannot be empty."})
    
@app.route('/add_deck_wikipedia', methods=['POST'])
def add_deck_wikipedia():
    deck_name = request.form['deck_name']
    lang_code = request.form['language']

    if not deck_name:
        return jsonify({"message": "Deck name is required."}), 400

    # Attempt to fetch the article
    article_content = fetch_wikipedia_article(deck_name, lang_code)

    # If article content is empty or fetch failed, return an error and don't create the deck
    if not article_content:
        return jsonify({"message": "Failed to fetch Wikipedia article. Please try again."}), 400

    # Continue with the normal processing if the article is fetched successfully
    clean_article = remove_references(article_content)
    word_freq = process_text(clean_article, lang_code)

    top_words = [word for word, _ in word_freq.most_common(100)]
    translations = translate_words(top_words, source_lang=lang_code, target_lang='en')

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO decks (name, language_code) VALUES (%s, %s)", (deck_name, lang_code))
    connection.commit()

    cursor.execute("SELECT LAST_INSERT_ID() AS id")
    deck_id = cursor.fetchone()['id']

    for source_word, translated_word in translations:
        cursor.execute("""INSERT INTO flashcards (term, definition, deck_id) VALUES (%s, %s, %s)""", (source_word, translated_word, deck_id))

    connection.commit()
    connection.close()

    return redirect(url_for('print_deck', deck_id=deck_id))

@app.route('/delete_deck/<int:deck_id>', methods=['POST'])
def delete_deck(deck_id):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM flashcards WHERE deck_id = %s", (deck_id,))
        cursor.execute("DELETE FROM decks WHERE id = %s", (deck_id,))
        connection.commit()
    connection.close()
    return redirect(url_for('index'))

@app.route('/add_flashcard/<int:deck_id>', methods=['POST'])
def add_flashcard(deck_id):
    term = request.form['term']
    definition = request.form['definition']

    if term and definition:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO flashcards (term, definition, deck_id)
            VALUES (%s, %s, %s)
        """, (term, definition, deck_id))

        connection.commit()
        connection.close()

        return redirect(url_for('print_deck', deck_id=deck_id))  
    else:
        return jsonify({"message": "Term and definition cannot be empty."})

@app.route('/delete_flashcard/<int:flashcard_id>', methods=['POST'])
def delete_flashcard(flashcard_id):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT deck_id FROM flashcards WHERE id = %s", (flashcard_id,))
        flashcard = cursor.fetchone()

        if flashcard is None:
            return "Flashcard not found!", 404 
        
        deck_id = flashcard['deck_id']

        cursor.execute("DELETE FROM flashcards WHERE id = %s", (flashcard_id,))

        connection.commit()

    connection.close()
    
    return redirect(url_for('print_deck', deck_id=deck_id))

@app.route('/update_flashcard/<int:flashcard_id>', methods=['GET','POST'])
def update_flashcard(flashcard_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    
    if request.method == 'GET':
        cursor.execute("SELECT * FROM flashcards WHERE id = %s", (flashcard_id,))
        flashcard = cursor.fetchone()

        if flashcard is None:
            connection.close()
            return "Flashcard not found", 404

        connection.close()
        return render_template('update_flashcard.html', flashcard=flashcard)  

    if request.method == 'POST':
            updated_term = request.form['term']
            updated_definition = request.form['definition']

            cursor.execute("SELECT deck_id FROM flashcards WHERE id = %s", (flashcard_id,))
            flashcard = cursor.fetchone()

            deck_id = flashcard['deck_id']

            cursor.execute("""
                UPDATE flashcards
                SET term = %s, definition = %s
                WHERE id = %s
            """, (updated_term, updated_definition, flashcard_id))

            connection.commit()
            connection.close()

            return redirect(url_for('print_deck', deck_id=deck_id)) 

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')  

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM decks WHERE name LIKE %s
    """, ('%' + query + '%',))
    decks_result = cursor.fetchall()

    cursor.execute("""
        SELECT * FROM flashcards WHERE term LIKE %s OR definition LIKE %s
    """, ('%' + query + '%', '%' + query + '%'))
    flashcards_result = cursor.fetchall()

    connection.close()

    return render_template('search_results.html', query=query, decks=decks_result, flashcards=flashcards_result)

# get session to have current_index start at 0. be able to recognize a new session 
@app.route('/review/<int:deck_id>', methods=['GET'])
def review(deck_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    
    cursor.execute("SELECT * FROM flashcards WHERE deck_id = %s", (deck_id,))
    flashcards = cursor.fetchall()
    connection.close()
    
    cards = []
    for row in flashcards:
        card = NewCard(
            id=str(row['id']),
            front=row['term'],
            back=row['definition'],
            last_reviewed=row['last_reviewed'],
            interval=row['spaced_interval'],
            ease=row['ease'],
            step=row['step'],
            status=row['status']
        )
        cards.append(card)

    # Check if new session or deck has changed
    if (
        'current_index' not in session or 
        'shuffled_ids' not in session or
        session.get('deck_id') != deck_id
    ):
        session['current_index'] = 0
        random.shuffle(cards)
        session['shuffled_ids'] = [card.id for card in cards]
        session['deck_id'] = deck_id  # Track current deck

    card_id_order = session.get('shuffled_ids', [])
    cards_dict = {card.id: card for card in cards}

    if session['current_index'] >= len(card_id_order):
        flashcard = None  # finished
    else:
        current_id = card_id_order[session['current_index']]
        current_card = cards_dict[current_id]
        flashcard = {
            "term": current_card.front,
            "definition": current_card.back,
            "id": current_card.id
        }

    return render_template('review.html', flashcard=flashcard)

@app.route('/merge_decks', methods=['POST'])
def merge_decks():
    deck_id_1 = int(request.form['deck1_id'])
    deck_id_2 = int(request.form['deck2_id'])
    new_deck_name = request.form['new_deck_name']

    connection = get_db_connection()
    cursor = connection.cursor()

    # Create the new deck
    cursor.execute("INSERT INTO decks (name) VALUES (%s)", (new_deck_name,))
    connection.commit()

    cursor.execute("SELECT LAST_INSERT_ID() AS id")
    new_deck_id = cursor.fetchone()['id']

    # Get flashcards from both decks
    cursor.execute("SELECT term, definition FROM flashcards WHERE deck_id = %s OR deck_id = %s", (deck_id_1, deck_id_2))
    flashcards = cursor.fetchall()

    # Insert flashcards into the new deck
    for card in flashcards:
        cursor.execute(
            "INSERT INTO flashcards (term, definition, deck_id) VALUES (%s, %s, %s)",
            (card['term'], card['definition'], new_deck_id)
        )

    connection.commit()
    connection.close()

    flash("Decks merged successfully!")
    return redirect(url_for('print_deck', deck_id=new_deck_id))


@app.route('/grade/<int:card_id>', methods=['POST'])
def grade(card_id):
    grade = request.form['grade']  
    
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM flashcards WHERE id = %s", (card_id,))
    row = cursor.fetchone()
    
    card = NewCard(
            id=str(row['id']),
            front=row['term'],
            back=row['definition'],
            last_reviewed=row['last_reviewed'],
            interval=row['spaced_interval'],
            ease=row['ease'],
            step=row['step'],
            status=row['status']
        )
    
    card.grade_answer(grade)  

    cursor.execute("""
        UPDATE flashcards 
        SET spaced_interval = %s, ease = %s, step = %s, status = %s, last_reviewed = %s
        WHERE id = %s
    """, (
        card.interval.total_seconds() if card.interval else None,
        card.ease,
        card.step,
        card.status,
        card.last_reviewed.strftime('%Y-%m-%d %H:%M:%S'),
        card_id
    ))

    connection.commit()
    connection.close()
    session['current_index'] +=1
   
    return redirect(url_for('review', deck_id=row['deck_id']))


if __name__ == '__main__':
    app.run(debug=True)
