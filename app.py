from flask import Flask, jsonify, request, render_template, redirect, url_for
from dotenv import load_dotenv
import os
import pymysql
import random
from simple_spaced_repetition import Card

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Get MySQL connection details from environment variables
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DB = os.getenv('MYSQL_DB')

# MySQL database connection
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
#interval = timedelta(seconds=row['interval_seconds']) if row['interval_seconds'] else None

@app.route('/')
def index():
    connection = get_db_connection()
    cursor = connection.cursor()
    
    # Fetch all the decks
    cursor.execute("SELECT * FROM decks")  # Make sure the 'decks' table exists and contains data
    decks = cursor.fetchall()
    connection.close()

    return render_template('index.html', decks=decks)

@app.route('/deck/<int:deck_id>', methods=['GET'])
def print_deck(deck_id):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        # Fetch deck's name based on id
        cursor.execute("SELECT name FROM decks WHERE id = %s",(deck_id,))
        deck=cursor.fetchone()

        if deck is None: 
            return "Deck not found!", 404
        
        deck_name = deck['name']
        # Fetch only flashcards for the given deck_id
        cursor.execute("SELECT * FROM flashcards WHERE deck_id = %s", (deck_id,))
        flashcards = cursor.fetchall()
    connection.close()
    
    if deck:
        return render_template('deck.html', deck_name=deck_name, flashcards=flashcards, deck_id=deck_id)


@app.route('/add_deck', methods=['POST'])
def add_deck():
    # Get the deck name from the form submission
    deck_name = request.form['deck_name']

    if deck_name:
        # Connect to the database and insert the new deck
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("INSERT INTO decks (name) VALUES (%s)", (deck_name,))
        connection.commit()

        connection.close()

        # Redirect to the homepage after adding the deck
        return redirect(url_for('index'))
    else:
        return jsonify({"message": "Deck name cannot be empty."})

@app.route('/add_flashcard/<int:deck_id>', methods=['POST'])
def add_flashcard(deck_id):
    term = request.form['term']
    definition = request.form['definition']

    if term and definition:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Insert the flashcard into the database, associating it with the deck_id
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
    # Get the deck_id of the flashcard to be deleted
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT deck_id FROM flashcards WHERE id = %s", (flashcard_id,))
        flashcard = cursor.fetchone()

        if flashcard is None:
            return "Flashcard not found!", 404  # Handle case where flashcard does not exist
        
        deck_id = flashcard['deck_id']

        # Option 1: Set the deck_id to NULL (removes flashcard from the deck but keeps it in the database)
        cursor.execute("UPDATE flashcards SET deck_id = NULL WHERE id = %s", (flashcard_id,))

        # Option 2: Alternatively, if you want to completely delete the flashcard, use:
        # cursor.execute("DELETE FROM flashcards WHERE id = %s", (flashcard_id,))

        connection.commit()

    connection.close()
    
    # After deletion, redirect to the deck page with the updated list of flashcards
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
        return render_template('update_flashcard.html', flashcard=flashcard)  # Render the update form with current flashcard data

    if request.method == 'POST':
            updated_term = request.form['term']
            updated_definition = request.form['definition']

            cursor.execute("SELECT deck_id FROM flashcards WHERE id = %s", (flashcard_id,))
            flashcard = cursor.fetchone()

            deck_id = flashcard['deck_id']

            # Update the flashcard in the database
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
    query = request.args.get('query')  # Get the search query from the user input

    connection = get_db_connection()
    cursor = connection.cursor()

    # Search for matching decks
    cursor.execute("""
        SELECT * FROM decks WHERE name LIKE %s
    """, ('%' + query + '%',))
    decks_result = cursor.fetchall()

    # Search for matching flashcards
    cursor.execute("""
        SELECT * FROM flashcards WHERE term LIKE %s OR definition LIKE %s
    """, ('%' + query + '%', '%' + query + '%'))
    flashcards_result = cursor.fetchall()

    connection.close()

    # Render a page with the search results
    return render_template('search_results.html', query=query, decks=decks_result, flashcards=flashcards_result)


if __name__ == '__main__':
    app.run(debug=True)
