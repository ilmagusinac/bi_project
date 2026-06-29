import os
from dotenv import load_dotenv
import psycopg

load_dotenv()

def get_connection():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DATABASE"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        sslmode=os.getenv("POSTGRES_SSLMODE", "require"),
    )

def test_connection():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), current_user, version();")
                database, user, version = cur.fetchone()

                print("Connection successful.")
                print(f"Database: {database}")
                print(f"User: {user}")
                print(f"PostgreSQL version: {version}")

    except Exception as error:
        print("Connection failed.")
        print(error)

if __name__ == "__main__":
    test_connection()