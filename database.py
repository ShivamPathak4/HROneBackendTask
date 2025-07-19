# database.py
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_database():
    """
    Returns a connection to the MongoDB database using the connection string
    from the environment variables.
    """
    # Get the connection string from the environment variable
    CONNECTION_STRING = os.getenv("MONGO_URI")
    
    # Check if the connection string is available
    if not CONNECTION_STRING:
        raise ValueError("No MONGO_URI found in environment variables")

    client = MongoClient(CONNECTION_STRING)
    return client['ecommerce']

# This is for standalone execution of this file.
if __name__ == "__main__":
    dbname = get_database()
    print(f"Connected to database: {dbname.name}")