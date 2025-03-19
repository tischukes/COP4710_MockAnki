import os

class Config:
    # Store database connection details (use environment variables for sensitive info)
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'your_password')
    MYSQL_DB = os.getenv('MYSQL_DB', 'books_db')
