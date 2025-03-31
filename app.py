from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv
import os
import pymysql

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

# Example route to show data from the database
@app.route('/')
def index():
    # Connect to the database and retrieve data
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM flashcards")  # Replace with your actual table name
        result = cursor.fetchall()
    connection.close()
    return jsonify(result)

#scroll through the flashcards deck here
@app.route('/review', methods=['GET'])
def review_flashcard():
    flashcard_id = request.args.get('flashcard_id', default=1, type=int)
    action = request.args.get('action', default=None, type=str)

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            # Query to get the total number of flashcards in the deck
            cursor.execute("SELECT COUNT(*) AS total_flashcards FROM flashcards")
            total_flashcards_result = cursor.fetchone()
            total_flashcards = total_flashcards_result['total_flashcards']

            # Fetch the current flashcard based on the flashcard_id
            if action == 'next':
                query = "SELECT * FROM flashcards WHERE id > %s ORDER BY id ASC LIMIT 1"
                cursor.execute(query, (flashcard_id,))
            elif action == 'previous':
                query = "SELECT * FROM flashcards WHERE id < %s ORDER BY id DESC LIMIT 1"
                cursor.execute(query, (flashcard_id,))
            else:
                query = "SELECT * FROM flashcards WHERE id = %s"
                cursor.execute(query, (flashcard_id,))
            
            flashcard = cursor.fetchone()

        if flashcard:
            # We may use another counter variable instead of 
            # using id since we want to generate order randomly in future
            flashcard_position = flashcard['id']
            flashcard_number = flashcard_position  

            return render_template('review.html', flashcard=flashcard, 
                                   flashcard_number=flashcard_number, total_flashcards=total_flashcards)

        return jsonify({"message": "No flashcard found"})
    finally:
        connection.close()

if __name__ == '__main__':
    app.run(debug=True)
