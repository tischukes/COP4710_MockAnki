from flask import Flask
from dotenv import load_dotenv
import os
import pymysql

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Get MySQL connection details from environment variables
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DB = os.getenv('MYSQL_DB')

# Connect to MySQL
def get_db_connection():
    connection = pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    return connection

@app.route('/')
def index():
    connection = get_db_connection()
    return "Connected to MySQL successfully!"

if __name__ == '__main__':
    app.run(debug=True)