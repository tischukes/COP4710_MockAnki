from flask import Flask, jsonify
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
        cursor.execute("SELECT * FROM books")  
        result = cursor.fetchall()
    connection.close()
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
